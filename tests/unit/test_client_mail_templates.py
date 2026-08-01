from types import SimpleNamespace

from app.api.v1.client_modules import _build_mail_template_context, _render_jinja


def test_dynamic_subject_uses_record_and_builtin_variables():
    client = SimpleNamespace(
        name="Ayatiworks",
        company_name="Ayatiworks Technologies",
        slug="ayatiworks",
    )
    module = SimpleNamespace(name="Therapy", slug="therapy")
    template = SimpleNamespace(name="New enquiry")

    context = _build_mail_template_context(
        {"name": "Srinath", "service": "Consultation"},
        client=client,
        module=module,
        template=template,
    )
    subject = _render_jinja(
        "New {{module_name}} enquiry from {{name}} | {{company_name}}",
        context,
    )

    assert subject == "New Therapy enquiry from Srinath | Ayatiworks Technologies"
    assert context["data"]["service"] == "Consultation"


def test_record_values_take_precedence_over_builtin_names():
    client = SimpleNamespace(name="Portal Client", company_name=None, slug="portal")

    context = _build_mail_template_context(
        {"company_name": "Submitted Company"},
        client=client,
    )

    assert context["company_name"] == "Submitted Company"
