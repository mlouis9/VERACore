FROM kitware/trame:glvnd
COPY --chown=trame-user:trame-user .deploy-release/setup /deploy/setup
RUN /opt/trame/entrypoint.sh build