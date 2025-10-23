# Imagen ligera para Terraform + Docker CLI
ARG TERRAFORM_VERSION=1.9.8
FROM alpine:latest

ARG TERRAFORM_VERSION

WORKDIR /workspace

# Instalar dependencias necesarias
RUN apk add --no-cache \
    curl \
    unzip \
    bash \
    docker-cli \
    git

# Descargar e instalar Terraform (validando la URL)
RUN set -eux; \
    ARCH=amd64; \
    TF_ZIP="terraform_${TERRAFORM_VERSION}_linux_${ARCH}.zip"; \
    URL="https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/${TF_ZIP}"; \
    echo "📦 Descargando Terraform desde $URL"; \
    curl -fsSL "$URL" -o /tmp/${TF_ZIP}; \
    unzip /tmp/${TF_ZIP} -d /usr/local/bin; \
    chmod +x /usr/local/bin/terraform; \
    terraform -version; \
    rm -f /tmp/${TF_ZIP}

# Usuario no root
RUN adduser -D terraform && chown terraform:terraform /workspace
USER terraform

ENTRYPOINT ["terraform"]
CMD ["-help"]

