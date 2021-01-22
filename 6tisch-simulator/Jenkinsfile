pipeline {
    agent {
        docker {
            image 'python:2.7'
            args '-e HOME=/tmp -e PATH=/tmp/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
        }
    }
    stages() {
        stage('Setup') {
            steps {
                sh 'git clean -f -d -x'
                sh 'pip install --user -r requirements.txt'
            }
        }
        stage('Test') {
            steps {
                sh 'pytest -x tests'
            }
        }
    }
}
