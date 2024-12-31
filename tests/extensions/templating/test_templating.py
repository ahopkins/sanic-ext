from pathlib import Path

from sanic import Sanic

from sanic_ext import render


def test_default_templates():
    app = Sanic("templating")
    app.extend(
        config={
            "templating_path_to_templates": Path(__file__).parent / "templates"
        }
    )

    @app.get("/1")
    @app.ext.template("foo.html")
    async def handler(_):
        return {"seq": ["one", "two"]}

    @app.get("/2")
    async def handler2(_):
        return await render(
            "foo.html", context={"seq": ["three", "four"]}, app=app
        )

    @app.get("/3")
    @app.ext.template("foo.html")
    async def handler3(_):
        return await render(
            context={"seq": ["five", "six"]}, status=201, app=app
        )

    @app.get("/4")
    async def handler4(_):
        response = await render(
            "foo.html", context={"seq": ["three", "four"]}, app=app
        )
        response.add_cookie("test", "foobar")
        return response

    _, response = app.test_client.get("/1")
    assert response.content_type == "text/html; charset=utf-8"
    assert "<li>one</li>" in response.text
    assert "<li>two</li>" in response.text

    _, response = app.test_client.get("/2")
    assert response.content_type == "text/html; charset=utf-8"
    assert "<li>three</li>" in response.text
    assert "<li>four</li>" in response.text

    _, response = app.test_client.get("/3")
    assert response.content_type == "text/html; charset=utf-8"
    assert "<li>five</li>" in response.text
    assert "<li>six</li>" in response.text
    assert response.status == 201

    _, response = app.test_client.get("/4")
    assert response.content_type == "text/html; charset=utf-8"
    assert "<li>three</li>" in response.text
    assert "<li>four</li>" in response.text
    assert response.cookies.get("test") == "foobar"


def test_render_from_string():
    app = Sanic("templating-from-string")
    app.extend()

    template = """
    <!DOCTYPE html>
<html lang="en">

    <head>
        <title>My Webpage</title>
    </head>

    <body>
        <h1>Hello, world!!!!</h1>
        <ul>
            {% for item in seq %}
            <li>{{ item }}</li>
            {% endfor %}
        </ul>
    </body>

</html>

    """

    @app.get("/2")
    async def handler2(_):
        return await render(
            template_source=template,
            context={"seq": ["three", "four"]},
            app=app,
        )

    _, response = app.test_client.get("/2")
    assert response.content_type == "text/html; charset=utf-8"
    assert "<li>three</li>" in response.text
    assert "<li>four</li>" in response.text


def test_config_templating_dir():
    app = Sanic("templating")
    app.config.TEMPLATING_PATH_TO_TEMPLATES = (
        Path(__file__).parent / "templates"
    )

    assert app.ext.templating.environment.get_template(
        "foo.html"
    ).filename == str(Path(__file__).parent / "templates" / "foo.html")


def test_url_for():
    app = Sanic("templating-from-string")
    app.extend()

    template = r"url: {{ url_for('handler') }}"

    @app.get("/one/two/three")
    async def handler(_):
        return await render(template_source=template)

    _, response = app.test_client.get("/one/two/three")
    assert response.text == "url: /one/two/three"


def test_default_context():
    app = Sanic("templating-from-string")
    app.extend(
        config={
            "templating_path_to_templates": Path(__file__).parent / "templates"
        }
    )

    template = r"{{ request.args.get('test') }}"

    @app.get("/1")
    async def handler1(_):
        return await render(template_source=template)

    @app.get("/2")
    @app.ext.template("request_test.html")
    async def handler2(_):
        return {}

    @app.get("/3")
    async def handler3(_):
        return await render("request_test.html", context={}, app=app)

    @app.get("/4")
    @app.ext.template("request_test.html")
    async def handler4(_):
        return await render(context={}, app=app)

    _, response = app.test_client.get("/1?test=passing")
    assert response.text == "passing"

    _, response = app.test_client.get("/2?test=passing")
    assert response.text == "passing"

    _, response = app.test_client.get("/3?test=passing")
    assert response.text == "passing"

    _, response = app.test_client.get("/4?test=passing")
    assert response.text == "passing"
