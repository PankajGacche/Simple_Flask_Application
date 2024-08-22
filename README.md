# Simple_Flask_Application
# Project Title

A brief description of your project, its purpose, and what it does.

## Table of Contents

- [Description](#description)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Features](#features)
- [Contributing](#contributing)
- [License](#license)
- [Contact Information](#contact-information)
- [Acknowledgments](#acknowledgments)

## Description

Provide a detailed description of your project. Explain its purpose, how it works, and what problems it solves.

## Installation

### Prerequisites

- List any prerequisites that need to be installed before setting up your project (e.g., Python, Node.js).

### Steps

## Step 4: Write ms1-deployment.yml describing the deployment of ms1.
```bash
apiVersion: apps/v1
kind: Deployment
metadata:
  name: microserver1-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: microserver1
  template:
    metadata:
      labels:
        app: microserver1
    spec:
      containers:
      - name: microserver1
        image: sukhilnair/mern:microservice1
        resources:
          limits:
            memory: "128Mi"
            cpu: "500m"
        ports:
        - containerPort: 3000
```

## Step 5: Write ms1-service.yml describing the service of ms1.

