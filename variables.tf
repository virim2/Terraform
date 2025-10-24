variable "mysql_root_password" {
  type    = string
  default = "rootpassword"
}

variable "mysql_database" {
  type    = string
  default = "appdb"
}

variable "mysql_user" {
  type    = string
  default = "appuser"
}

variable "mysql_password" {
  type    = string
  default = "apppassword"
}

variable "secret_key" {
  type    = string
  default = "s3cr3t-k3y-fl4sk-2025"
}

variable "redis_host" {
  type    = string
  default = "redis"
}

variable "redis_port" {
  type    = number
  default = 6379
}
