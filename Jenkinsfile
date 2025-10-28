pipeline {
    agent any
    environment {
        DOCKER_REGISTRY = 'localhost:5000'
        APP_NAME = 'flask-app'
        TERRAFORM_DIR = './terraform'
        APP_DIR = './app'
    }
    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', 
                url: 'https://github.com/ingivangaleno-reyes/Terraform.git'
                echo '✅ Código descargado correctamente'
            }
        }
        
        stage('Build Docker Images') {
            steps {
                dir(APP_DIR) {
                    sh """
                    docker build -t ${APP_NAME}:${BUILD_NUMBER} .
                    docker tag ${APP_NAME}:${BUILD_NUMBER} ${APP_NAME}:latest
                    """
                }
            }
        }
        
        stage('Run Basic Tests') {
            steps {
                sh """
                docker run --rm ${APP_NAME}:${BUILD_NUMBER} python -c \"import flask; print('Flask import successful')\"
                docker run --rm ${APP_NAME}:${BUILD_NUMBER} python -c \"import redis; print('Redis import successful')\"
                docker run --rm ${APP_NAME}:${BUILD_NUMBER} python -c \"import pymysql; print('MySQL import successful')\"
                """
            }
        }
        
        stage('Terraform Plan') {
            steps {
                dir(TERRAFORM_DIR) {
                    sh 'terraform init'
                    sh 'terraform plan -out=tfplan'
                }
            }
        }
        
        stage('Manual Approval') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    input message: '¿Proceder con el deployment?', 
                          ok: 'Deploy'
                }
            }
        }
        
        stage('Terraform Apply') {
            steps {
                dir(TERRAFORM_DIR) {
                    sh 'terraform apply -auto-approve tfplan'
                }
            }
        }
        
        stage('Smoke Test') {
            steps {
                script {
                    // Esperar a que la aplicación esté lista
                    sleep 30
                    // Test básico de conectividad
                    sh 'curl -f http://localhost:5000/ || exit 1'
                    echo ' Aplicación desplegada correctamente'
                }
            }
        }
    }
    
    post {
        always {
            echo 'Pipeline completado'
            // Limpiar contenedores temporales
            sh 'docker system prune -f'
        }
        success {
            echo ' Pipeline exitoso'
        }
        failure {
            echo ' Pipeline falló'
        }
    }
}
