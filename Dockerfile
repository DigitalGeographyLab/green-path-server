FROM continuumio/miniconda3

ADD src /src
WORKDIR /src
RUN conda env create -f /src/conda-env.yml && conda clean -afy
ENV PATH /opt/conda/envs/gp-env/bin:$PATH

CMD ["/start-application.sh"]