FROM mcr.microsoft.com/devcontainers/python:1-3.10-bookworm
ARG PATH_TO_REPO="/workspaces/bsm2-python"
COPY .. ${PATH_TO_REPO}
# ARG PATH_TO_VERSION_PY="src/bsm2_python/_version.py"
# COPY pyproject.toml ${PATH_TO_REPO}/pyproject.toml
# COPY README.md ${PATH_TO_REPO}/README.md
# COPY .git ${PATH_TO_REPO}/.git
# COPY ${PATH_TO_VERSION_PY} ${PATH_TO_REPO}/${PATH_TO_VERSION_PY}
RUN chmod -R 777 ${PATH_TO_REPO}
RUN git config --global --add safe.directory ${PATH_TO_REPO}
RUN pip install pipx
RUN pipx install hatch
# now install all environments from pyproject.toml
WORKDIR ${PATH_TO_REPO}
RUN pipx install pre-commit
RUN hatch run pre-commit install
RUN hatch run python -V
RUN hatch run test:python -V
RUN hatch run docs:python -V
RUN hatch run lint:python -V
# get path to python executable from hatch env find test
RUN echo "PATH_TO_TEST_ENV=$(hatch env find test)/bin/python" >> /root/.bashrc
# for mkdocs, cairo needs to be installed
RUN apt update && apt install -y libcairo2-dev git-lfs
