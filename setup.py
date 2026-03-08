from setuptools import find_packages, setup

setup(
    name="multi-agent-requirement-review-system",
    version="0.6.0",
    description="LangGraph-based requirement review and delivery planning workflow",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.11",
    packages=find_packages(include=["requirement_review_v1*", "review_runtime*"]),
)
