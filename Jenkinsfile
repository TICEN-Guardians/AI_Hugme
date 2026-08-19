pipeline {
    agent any

    environment {
        AWS_REGION = 'ap-northeast-2'
        ECR_REGISTRY = '852891424427.dkr.ecr.ap-northeast-2.amazonaws.com'
        IMAGE_NAME = 'hugme-ai'

        AI_INSTANCE_ID = 'i-069c22edace08a510'
        AI_DEPLOY_DIR = '/opt/hugme/ai'
        STABLE_PARAMETER = '/hugme/ai/stable-sha'
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

        stage('Prepare Deploy') {
            steps {
                script {
                    env.PREVIOUS_STABLE_SHA = sh(
                        script: '''
                            aws ssm get-parameter \
                            --name "$STABLE_PARAMETER" \
                            --query 'Parameter.Value' \
                            --output text \
                            --region "$AWS_REGION"
                        ''',
                        returnStdout: true
                    ).trim()
                }

                sh 'echo "PREVIOUS_STABLE_SHA=$PREVIOUS_STABLE_SHA"'

                sh '''
                    aws ecr describe-images \
                    --repository-name "$IMAGE_NAME" \
                    --image-ids imageTag="$PREVIOUS_STABLE_SHA" \
                    --region "$AWS_REGION"
                '''
            }
        }

        stage('SSM Deploy') {
            steps {
                script {
                    def deployScript = '''#!/usr/bin/env bash

set -u

AWS_REGION="__AWS_REGION__"
ECR_REGISTRY="__ECR_REGISTRY__"
DEPLOY_DIR="__DEPLOY_DIR__"
NEW_SHA="__NEW_SHA__"
PREVIOUS_SHA="__PREVIOUS_SHA__"

health_check() {
    local label="$1"

    for i in $(seq 1 30); do
        response="$(curl -fsS http://127.0.0.1:8000/health 2>/dev/null || true)"

        if printf '%s' "$response" | grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"'; then
            echo "$label Health Check 성공"
            echo "$response"
            return 0
        fi

        echo "$label Health Check 대기 중 ($i/30)"
        sleep 10
    done

    return 1
}

rollback() {
    echo "Rollback 시작"
    echo "Rollback SHA=$PREVIOUS_SHA"

    cd "$DEPLOY_DIR" || return 1

    sed -i "s/^AI_IMAGE_TAG=.*/AI_IMAGE_TAG=$PREVIOUS_SHA/" .deploy.env

    if ! docker compose --env-file .env --env-file .deploy.env pull fastapi; then
        echo "Rollback Image Pull 실패"
        return 1
    fi

    if ! docker compose --env-file .env --env-file .deploy.env up -d fastapi; then
        echo "Rollback Container 실행 실패"
        return 1
    fi

    if health_check "Rollback"; then
        echo "Rollback 완료"
        return 0
    fi

    echo "Rollback Health Check 실패"
    docker logs --tail 200 hugme-ai-app || true
    return 1
}

cd "$DEPLOY_DIR" || exit 1

echo "AI 배포 시작"
echo "NEW_SHA=$NEW_SHA"
echo "PREVIOUS_SHA=$PREVIOUS_SHA"

if ! aws ecr get-login-password --region "$AWS_REGION" \
    | docker login \
    --username AWS \
    --password-stdin "$ECR_REGISTRY"; then
    echo "ECR Login 실패"
    exit 1
fi

sed -i "s/^AI_IMAGE_TAG=.*/AI_IMAGE_TAG=$NEW_SHA/" .deploy.env

if ! docker compose --env-file .env --env-file .deploy.env pull fastapi; then
    echo "새 AI Image Pull 실패"

    sed -i "s/^AI_IMAGE_TAG=.*/AI_IMAGE_TAG=$PREVIOUS_SHA/" .deploy.env

    exit 1
fi

if ! docker compose --env-file .env --env-file .deploy.env up -d fastapi; then
    echo "새 AI Container 실행 실패"

    if rollback; then
        echo "기존 정상 버전으로 Rollback 성공"
    else
        echo "Rollback 실패"
    fi

    exit 1
fi

if health_check "새 AI"; then
    echo "새 AI 배포 성공"
    exit 0
fi

echo "새 AI Health Check 실패"
docker logs --tail 200 hugme-ai-app || true

if rollback; then
    echo "기존 정상 버전으로 Rollback 성공"
else
    echo "Rollback 실패"
fi

exit 1
'''

                    deployScript = deployScript
                        .replace('__AWS_REGION__', env.AWS_REGION)
                        .replace('__ECR_REGISTRY__', env.ECR_REGISTRY)
                        .replace('__DEPLOY_DIR__', env.AI_DEPLOY_DIR)
                        .replace('__NEW_SHA__', env.GIT_SHA)
                        .replace('__PREVIOUS_SHA__', env.PREVIOUS_STABLE_SHA)

                    writeFile(
                        file: 'deploy-ai.sh',
                        text: deployScript
                    )

                    env.DEPLOY_SCRIPT_B64 = sh(
                        script: '''
                            base64 deploy-ai.sh | tr -d '\\n'
                        ''',
                        returnStdout: true
                    ).trim()
                }

                sh '''
                    jq -n \
                    --arg instance "$AI_INSTANCE_ID" \
                    --arg script "$DEPLOY_SCRIPT_B64" \
                    '{
                        DocumentName: "AWS-RunShellScript",
                        InstanceIds: [$instance],
                        Parameters: {
                            commands: [
                                ("echo " + $script + " | base64 -d > /tmp/hugme-ai-deploy.sh"),
                                "chmod +x /tmp/hugme-ai-deploy.sh",
                                "/tmp/hugme-ai-deploy.sh"
                            ],
                            executionTimeout: ["1200"]
                        }
                    }' > ssm-deploy.json
                '''

                script {
                    env.COMMAND_ID = sh(
                        script: '''
                            aws ssm send-command \
                            --cli-input-json file://ssm-deploy.json \
                            --region "$AWS_REGION" \
                            --query 'Command.CommandId' \
                            --output text
                        ''',
                        returnStdout: true
                    ).trim()
                }

                sh 'echo "COMMAND_ID=$COMMAND_ID"'

                sh '''
                    FINAL_STATUS=""

                    for i in $(seq 1 120); do
                        STATUS=$(aws ssm get-command-invocation \
                            --command-id "$COMMAND_ID" \
                            --instance-id "$AI_INSTANCE_ID" \
                            --region "$AWS_REGION" \
                            --query 'Status' \
                            --output text 2>/dev/null || true)

                        echo "SSM 상태 확인 ($i/120): $STATUS"

                        case "$STATUS" in
                            Success)
                                FINAL_STATUS="$STATUS"
                                break
                                ;;
                            Failed|Cancelled|TimedOut|Cancelling)
                                FINAL_STATUS="$STATUS"
                                break
                                ;;
                        esac

                        sleep 10
                    done

                    aws ssm get-command-invocation \
                        --command-id "$COMMAND_ID" \
                        --instance-id "$AI_INSTANCE_ID" \
                        --region "$AWS_REGION" \
                        --query '{
                            Status:Status,
                            ResponseCode:ResponseCode,
                            StandardOutputContent:StandardOutputContent,
                            StandardErrorContent:StandardErrorContent
                        }' \
                        --output json

                    if [ "$FINAL_STATUS" != "Success" ]; then
                        echo "AI SSM 배포 실패"
                        exit 1
                    fi
                '''
            }
        }

        stage('Update Stable SHA') {
            steps {
                sh '''
                    aws ssm put-parameter \
                    --name "$STABLE_PARAMETER" \
                    --type String \
                    --value "$GIT_SHA" \
                    --overwrite \
                    --region "$AWS_REGION"
                '''

                sh '''
                    STABLE_SHA=$(aws ssm get-parameter \
                        --name "$STABLE_PARAMETER" \
                        --query 'Parameter.Value' \
                        --output text \
                        --region "$AWS_REGION")

                    echo "STABLE_SHA=$STABLE_SHA"

                    if [ "$STABLE_SHA" != "$GIT_SHA" ]; then
                        echo "Stable SHA 갱신 확인 실패"
                        exit 1
                    fi
                '''
            }
        }
    }

    post {
        success {
            echo 'AI CI/CD Pipeline 전체 성공'
        }

        failure {
            echo 'AI CI/CD Pipeline 실패'
        }
    }
}