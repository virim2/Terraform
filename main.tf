terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = ">= 2.20.0"
    }
    local = {
      source  = "hashicorp/local"
      version = ">= 2.0.0"
    }
  }
}

provider "docker" {
  # Ejecuta terraform donde esté accesible el docker daemon (GNS3VM): socket unix
  host = "unix:///var/run/docker.sock"
}

# network para resolución por nombre (como docker-compose)
resource "docker_network" "lab_net" {
  name = "lab_network"
}

# Build image de la app desde ./app
resource "docker_image" "flask_app" {
  name = "flask_app_local:name"

  build {
    context    = "${path.module}/app"
    dockerfile = "Dockerfile"
  }
}

# MySQL container
resource "docker_container" "mysql" {
  name  = "lab_mysql"
  image = "mysql:8.0"

  env = [
    "MYSQL_ROOT_PASSWORD=${var.mysql_root_password}",
    "MYSQL_DATABASE=${var.mysql_database}",
    "MYSQL_USER=${var.mysql_user}",
    "MYSQL_PASSWORD=${var.mysql_password}"
  ]

  ports {
    internal = 3306
    external = 3306
  }

  volumes {
    host_path      = "/terraform/db"
    container_path = "/var/lib/mysql"
  }

  # Volumen para scripts de inicialización
  volumes {
    host_path      = abspath("./db/init.sql")
    container_path = "/docker-entrypoint-initdb.d/init.sql"
   
  }


  networks_advanced {
    name = docker_network.lab_net.name
  }

  # esperar que el contenedor suba antes del app
  restart = "no"
}

# Flask container (usa la imagen construida)
resource "docker_container" "flask" {
  name  = "lab_flask"
  image = docker_image.flask_app.name

  env = [
    "SECRET_KEY=${var.secret_key}",
    "MYSQL_HOST=${docker_container.mysql.name}",
    "MYSQL_PORT=3306",
    "MYSQL_USER=${var.mysql_user}",
    "MYSQL_PASSWORD=${var.mysql_password}",
    "MYSQL_DATABASE=${var.mysql_database}"
  ]

  ports {
    internal = 5000
    external = 5000
  }

  networks_advanced {
    name = docker_network.lab_net.name
  }

  depends_on = [docker_container.mysql]
  # restart = "unless-stopped"   # opcional
}

