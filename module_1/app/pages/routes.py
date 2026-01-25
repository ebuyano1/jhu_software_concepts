# Routes for the personal developer website:
# - "/" home page (bio + image)
# - "/projects" module 1 project info + GitHub link
# - "/contact" email + LinkedIn

from flask import Blueprint, render_template

main_pages_blueprint = Blueprint("pages", __name__)

@main_pages_blueprint.get("/")
def home():
    return render_template(
        "home.html",
        page_title="Home",

        # My name and introduction
        name="Eugene Buyanovsky",
        position="MS in Artificial Intelligence Student at Johns Hopkins University",

        bio=(
        "Hi everyone my name is Eugene. I live in New Jersey and have been working in IT industry for several years. "
            "I am a self taught programmer and used to develop .NET Web Applications using VB.NET and C#. I need to sharpen my skills again so I am doing a MS in AI at JHU "
            "as I am now into building AI agents, model context protocol servers and leveraging large language models to solve business problems, automate work. "
            "I am excited about learning Modern software concepts. I have taken formal CS courses such as data structures (I loved linked lists and sorting algorithms)."
              " Looking forward to learning together."
           
        ),

        # My contact information
        email="ebuyano1@jh.edu",
        linkedin_text="linkedin.com/in/ebuyan",
        linkedin_url="https://www.linkedin.com/in/ebuyan/",

        # My photo in static folder
        image_filename="eugene_photo.jpg",
    )

@main_pages_blueprint.get("/projects")
def projects():
    return render_template(
        "projects.html",
        page_title="Projects",

        module1_title="Module 1 - Project",
        module1_details=(
            "This is a personal website, "
            "I am building it with Flask and Python."
        ),
        github_url="https://github.com/ebuyano1/jhu_software_concepts\module_1",
    )

@main_pages_blueprint.get("/contact")
def contact():
    return render_template(
        "contact.html",
        page_title="Contact",
        email="ebuyano1@jh.edu",
        linkedin_text="linkedin.com/in/ebuyan",
        linkedin_url="https://www.linkedin.com/in/ebuyan/",
    )
