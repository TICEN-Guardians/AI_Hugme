pipeline {
    agent any

    environment {
        AWS_REGION = 'ap-northeast-2'
        ECR_REGISTRY = '852891424427.dkr.ecr.ap-northeast-2.amazonaws.com'
        IMAGE_NAME = 'hugme-ai'
    }

    options {
        skipDefaultCheckout(true)
        timestamps()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Prepare') {
            steps {
                script {
                    env.GIT_SHA = sh(
                        script: 'git rev-parse HEAD',
                        returnStdout: true
                    ).trim()

                    env.IMAGE_URI = "${env.ECR_REGISTRY}/${env.IMAGE_NAME}:${env.GIT_SHA}"
                    env.LATEST_IMAGE_URI = "${env.ECR_REGISTRY}/${env.IMAGE_NAME}:latest"
                }

                sh 'echo "GIT_SHA=$GIT_SHA"'
                sh 'echo "IMAGE_URI=$IMAGE_URI"'
                sh 'echo "LATEST_IMAGE_URI=$LATEST_IMAGE_URI"'
            }
        }

        stage('Syntax Check') {
            steps {
                sh '''
                    docker run --rm \
                    -v "$WORKSPACE:/workspace:ro" \
                    -w /workspace \
                    python:3.13-slim \
                    python -c 'import ast, pathlib; files=list(pathlib.Path("app").rglob("*.py")); [ast.parse(p.read_text(encoding="utf-8")) for p in files]; print(f"Python syntax check passed: {len(files)} files")'
                '''
            }
        }

        stage('Docker Build') {
            steps {
                sh 'docker build -t "$IMAGE_URI" .'
                sh 'docker image inspect "$IMAGE_URI" --format "{{.Id}}"'
            }
        }

        stage('ECR Login') {
            steps {
                sh '''
                    aws ecr get-login-password --region "$AWS_REGION" \
                    | docker login \
                    --username AWS \
                    --password-stdin "$ECR_REGISTRY"
                '''
            }
        }

        stage('ECR Push') {
            steps {
                sh 'docker tag "$IMAGE_URI" "$LATEST_IMAGE_URI"'
                sh 'docker push "$IMAGE_URI"'
                sh 'docker push "$LATEST_IMAGE_URI"'
            }
        }

        stage('ECR Verify') {
            steps {
                sh '''
                    aws ecr describe-images \
                    --repository-name "$IMAGE_NAME" \
                    --image-ids imageTag="$GIT_SHA" \
                    --region "$AWS_REGION"
                '''

                sh '''
                    aws ecr describe-images \
                    --repository-name "$IMAGE_NAME" \
                    --image-ids imageTag=latest \
                    --region "$AWS_REGION"
                '''
            }
        }
    }

    post {
        success {
            echo 'AI Test / Docker Build / ECR Push 성공'
        }

        failure {
            echo 'AI Test / Docker Build / ECR Push 실패'
        }
    }
}