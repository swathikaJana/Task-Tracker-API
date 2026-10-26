pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Environment Check') {
            steps {
                sh 'python3 --version'
                sh 'git --version'
            }
        }

        stage('Create Virtual Environment') {
            steps {
                sh 'python3 -m venv .venv'
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '.venv/bin/python -m pip install -r requirements-dev.txt'
            }
        }

        stage('Run Tests') {
            steps {
                sh '.venv/bin/python -m pytest -v tests/'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t task-tracker-platform:${BUILD_NUMBER} .'
            }
        }

        stage('Push Docker Image') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'scratch2devops',
                    usernameVariable: 'DOCKERHUB_USERNAME',
                    passwordVariable: 'DOCKERHUB_TOKEN'
                )]) {
                    sh '''
                        set -e
                        trap 'docker logout >/dev/null 2>&1 || true' EXIT

                        echo "$DOCKERHUB_TOKEN" | docker login \
                            --username "$DOCKERHUB_USERNAME" \
                            --password-stdin

                        docker tag "task-tracker-platform:$BUILD_NUMBER" \
                            "$DOCKERHUB_USERNAME/task-tracker-platform:$BUILD_NUMBER"

                        docker push \
                            "$DOCKERHUB_USERNAME/task-tracker-platform:$BUILD_NUMBER"
                    '''
                }
            }
        }

        stage('Deploy') {
            steps {
                withCredentials([
                    string(
                        credentialsId: 'task-tracker-db-password',
                        variable: 'DB_PASSWORD'
                    ),
                    usernamePassword(
                        credentialsId: 'scratch2devops',
                        usernameVariable: 'DOCKERHUB_USERNAME',
                        passwordVariable: 'DOCKERHUB_TOKEN'
                    )
                ]) {
                    sh '''
                        set -e
                        trap 'docker logout >/dev/null 2>&1 || true' EXIT

                        # During the one-time transition the old API is
                        # task-tracker-platform-api-1. Later runs use the
                        # standardized task-tracker-api project.
                        PREVIOUS_CONTAINER=task-tracker-api-api-1
                        if ! docker inspect "$PREVIOUS_CONTAINER" >/dev/null 2>&1; then
                            PREVIOUS_CONTAINER=task-tracker-platform-api-1
                        fi

                        PREVIOUS_IMAGE=$(docker inspect "$PREVIOUS_CONTAINER" \
                            --format '{{.Config.Image}}')
                        PREVIOUS_TAG="${PREVIOUS_IMAGE##*:}"

                        echo "Previous API image: $PREVIOUS_IMAGE"
                        export IMAGE_TAG="$BUILD_NUMBER"

                        echo "$DOCKERHUB_TOKEN" | docker login \
                            --username "$DOCKERHUB_USERNAME" \
                            --password-stdin

                        docker compose -p task-tracker-api pull api

                        # Free port 8002 on the first deployment. This stops
                        # only the legacy API; it leaves DB, Redis, and volumes alone.
                        docker compose -p task-tracker-platform stop api || true

                        deploy_and_verify() {
                            docker compose -p task-tracker-api up -d --no-deps api

                            container=$(docker compose -p task-tracker-api ps -q api)
                            if [ -z "$container" ]; then
                                echo "ERROR: Compose did not create the API container."
                                return 1
                            fi

                            echo "Waiting for API health..."
                            healthy=false

                            for attempt in $(seq 1 18); do
                                health=$(docker inspect "$container" \
                                    --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}')

                                echo "Health check attempt $attempt/18: $health"

                                if [ "$health" = "healthy" ]; then
                                    healthy=true
                                    break
                                fi

                                if [ "$health" = "unhealthy" ] || [ "$health" = "no-healthcheck" ]; then
                                    echo "ERROR: API container health is $health."
                                    return 1
                                fi

                                sleep 5
                            done

                            if [ "$healthy" != "true" ]; then
                                echo "ERROR: API did not become healthy in time."
                                return 1
                            fi

                            response=$(docker exec "$container" python -c \
                               "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read().decode())") || return 1

                            echo "Health endpoint response: $response"
                            echo "$response" | grep -q '"status":"ok"' || {
                                echo "ERROR: Health endpoint returned an unexpected response."
                                return 1
                            }
                        }

                        if deploy_and_verify; then
                            echo "Deployment successful."
                        else
                            echo "ERROR: Deployment failed. Restoring $PREVIOUS_IMAGE."

                            export IMAGE_TAG="$PREVIOUS_TAG"

                            if docker compose -p task-tracker-api pull api \
                                && deploy_and_verify; then
                                echo "Rollback successful. Previous API is healthy."
                            else
                                echo "CRITICAL: Rollback failed. Check the API container and Jenkins log."
                            fi

                            exit 1
                        fi
                    '''
                }
            }
        }
    }

    post {
        success {
            echo 'CI pipeline completed successfully.'
        }
        failure {
            echo 'CI pipeline failed. Check the console output.'
        }
        always {
            echo 'CI pipeline execution finished.'
        }
    }
}
