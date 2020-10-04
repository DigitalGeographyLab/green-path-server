FROM continuumio/miniconda3

ADD src /src
WORKDIR /src
RUN conda env create -f /src/env/conda-env.yml && conda clean -afy
ENV PATH /opt/conda/envs/gp-env/bin:$PATH

RUN chmod +x start-application.sh
CMD ./start-application.sh