import inspect

from functools import lru_cache, partial
from os.path import abspath, dirname, realpath

from sanic import Request
from sanic.blueprints import Blueprint
from sanic.config import Config
from sanic.log import logger
from sanic.response import file, html, json

from sanic_ext.config import PRIORITY
from sanic_ext.extensions.openapi.builders import (
    OperationStore,
    SpecificationBuilder,
)

from ...utils.route import (
    clean_route_name,
    get_all_routes,
    get_blueprinted_routes,
)


@lru_cache
def get_oauth2_redirect_html(version: str):
    import urllib

    response = urllib.request.urlopen(
        f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{version}/"
        "oauth2-redirect.html"
    ).read()

    return response.decode("utf-8")


def oauth2_handler(request: Request, version: str):
    return html(get_oauth2_redirect_html(version))


def blueprint_factory(config: Config):
    bp = Blueprint("openapi", url_prefix=config.OAS_URL_PREFIX)

    dir_path = dirname(realpath(__file__))
    dir_path = abspath(dir_path + "/ui")

    for ui in ("redoc", "swagger"):
        if getattr(config, f"OAS_UI_{ui}".upper()):
            path = getattr(config, f"OAS_PATH_TO_{ui}_HTML".upper())
            uri = getattr(config, f"OAS_URI_TO_{ui}".upper())
            version = getattr(config, f"OAS_UI_{ui}_VERSION".upper(), "")
            html_title = getattr(config, f"OAS_UI_{ui}_HTML_TITLE".upper())
            custom_css = getattr(config, f"OAS_UI_{ui}_CUSTOM_CSS".upper())
            html_path = path if path else f"{dir_path}/{ui}.html"

            with open(html_path, "r") as f:
                page = f.read()

            def index(
                request: Request, page: str, html_title: str, custom_css: str
            ):
                prefix = (
                    request.app.url_for("openapi.index", _external=True)
                    if getattr(request.app.config, "SERVER_NAME", None)
                    else getattr(request.app.config, "OAS_URL_PREFIX")
                ).rstrip("/")
                config_uri = getattr(request.app.config, "OAS_URI_TO_CONFIG")
                config_json = getattr(request.app.config, "OAS_URI_TO_JSON")
                return html(
                    page.replace("__VERSION__", version)
                    .replace("__URL_PREFIX__", prefix)
                    .replace("__URL_CONFIG__", config_uri)
                    .replace("__URL_JSON__", config_json)
                    .replace("__HTML_TITLE__", html_title)
                    .replace("__HTML_CUSTOM_CSS__", custom_css)
                )

            bp.add_route(
                partial(
                    index,
                    page=page,
                    html_title=html_title,
                    custom_css=custom_css,
                ),
                uri,
                name=ui,
            )
            if config.OAS_UI_DEFAULT and config.OAS_UI_DEFAULT == ui:
                bp.add_route(
                    partial(
                        index,
                        page=page,
                        html_title=html_title,
                        custom_css=custom_css,
                    ),
                    "",
                    name="index",
                )

            if ui == "swagger":
                oauth2_redirect_uri = getattr(
                    config, "OAS_UI_SWAGGER_OAUTH2_REDIRECT"
                )

                bp.add_route(
                    partial(oauth2_handler, version=version),
                    oauth2_redirect_uri,
                    name="oauth2-redirect",
                )

    @bp.get(config.OAS_URI_TO_JSON)
    async def spec(request: Request):
        if config.OAS_CUSTOM_FILE:
            return await file(config.OAS_CUSTOM_FILE)
        return json(SpecificationBuilder().build(request.app).serialize())

    if config.OAS_UI_SWAGGER:

        @bp.get(config.OAS_URI_TO_CONFIG)
        def openapi_config(request: Request):
            return json(request.app.config.SWAGGER_UI_CONFIGURATION)

    @bp.before_server_start(priority=PRIORITY)
    def build_spec(app, loop):
        specification = SpecificationBuilder()
        # --------------------------------------------------------------- #
        # Blueprint Tags
        # --------------------------------------------------------------- #

        for blueprint_name, handler in get_blueprinted_routes(app):
            operation = OperationStore()[handler]
            if not operation.tags:
                operation.tag(blueprint_name)

        # --------------------------------------------------------------- #
        # Operations
        # --------------------------------------------------------------- #
        for (
            uri,
            route_name,
            route_parameters,
            method_handlers,
            host,
        ) in get_all_routes(app, bp.url_prefix):
            # --------------------------------------------------------------- #
            # Methods
            # --------------------------------------------------------------- #

            for method, _handler in method_handlers:
                if (
                    (method == "OPTIONS" and app.config.OAS_IGNORE_OPTIONS)
                    or (method == "HEAD" and app.config.OAS_IGNORE_HEAD)
                    or method == "TRACE"
                ):
                    continue

                if hasattr(_handler, "view_class"):
                    _handler = getattr(_handler.view_class, method.lower())
                store = OperationStore()
                if (
                    _handler not in store
                    and (func := getattr(_handler, "__func__", None))
                    and func in store
                ):
                    _handler = func
                operation = store[_handler]

                if operation._exclude or "openapi" in operation.tags:
                    continue

                docstring = inspect.getdoc(_handler)

                if (
                    docstring
                    and app.config.OAS_AUTODOC
                    and operation._allow_autodoc
                ):
                    operation.autodoc(docstring)

                operation._default["operationId"] = (
                    f"{method.lower()}~{route_name}"
                )
                operation._default["summary"] = clean_route_name(route_name)

                if host:
                    if "servers" not in operation._default:
                        operation._default["servers"] = []
                    operation._default["servers"].append({"url": f"//{host}"})

                for _parameter in route_parameters:
                    if any(
                        (
                            param.fields["name"] == _parameter.name
                            for param in operation.parameters
                        )
                    ):
                        continue

                    kwargs = {}
                    if operation._autodoc and (
                        parameters := operation._autodoc.get("parameters")
                    ):
                        for param in parameters:
                            if param.pop("name", None) == _parameter.name:
                                kwargs["description"] = param.get(
                                    "description"
                                )
                                kwargs["required"] = param.get("required")
                                if schema := param.get("schema"):
                                    logger.warning(
                                        f"Ignoring the schema {schema} in "
                                        f"'{route_name}' for "
                                        f"'{_parameter.name}'. "
                                        "Instead of using the definition in "
                                        "docstring definition, Sanic will use "
                                        "the actual schema defined for this "
                                        "parameter on the route."
                                    )
                                break

                    operation.parameter(
                        _parameter.name, _parameter.cast, "path", **kwargs
                    )

                operation._app = app
                specification.operation(uri, method, operation)

        add_static_info_to_spec_from_config(app, specification)

    return bp


def add_static_info_to_spec_from_config(app, specification):
    """
    Reads app.config and sets attributes to specification according to the
    desired values.

    Modifies specification in-place and returns None
    """
    specification._do_describe(
        getattr(app.config, "API_TITLE", "API"),
        getattr(app.config, "API_VERSION", "1.0.0"),
        getattr(app.config, "API_DESCRIPTION", None),
        getattr(app.config, "API_TERMS_OF_SERVICE", None),
    )

    specification._do_license(
        getattr(app.config, "API_LICENSE_NAME", None),
        getattr(app.config, "API_LICENSE_URL", None),
    )

    specification._do_contact(
        getattr(app.config, "API_CONTACT_NAME", None),
        getattr(app.config, "API_CONTACT_URL", None),
        getattr(app.config, "API_CONTACT_EMAIL", None),
    )

    schemes = getattr(app.config, "API_SCHEMES", ["http"]) or ["http"]
    if isinstance(schemes, str):
        schemes = [s.strip() for s in schemes.split(",")]
    for scheme in schemes:
        host = getattr(app.config, "API_HOST", None)
        basePath = getattr(app.config, "API_BASEPATH", "")
        if host is None or basePath is None:
            continue

        specification.url(f"{scheme}://{host}/{basePath}")
