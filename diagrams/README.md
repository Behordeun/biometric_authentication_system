# Architecture Diagrams

This directory contains Mermaid diagrams for the Hybrid Passwordless Authentication System.

## Diagrams Overview

### 1. System Architecture (`system-architecture.mmd`)
High-level system architecture showing all components and their interactions for IaaS deployment.

### 2. Infrastructure Deployment (`infrastructure-deployment.mmd`)
Detailed infrastructure diagram showing multi-AZ deployment, load balancing, databases, caching, monitoring, and CI/CD pipeline.

### 3. Database Schema (`database-schema.mmd`)
Entity-relationship diagram showing all database tables and their relationships.

### 4. User Registration Flow (`user-registration-flow.mmd`)
Flowchart showing the complete user registration process with biometric authentication.

### 5. User Login Flow (`user-login-flow.mmd`)
Flowchart showing the complete user login process with biometric authentication.

### 6. Registration Sequence (`registration-sequence.mmd`)
Detailed sequence diagram showing all interactions during user registration.

### 7. Login Sequence (`login-sequence.mmd`)
Detailed sequence diagram showing all interactions during user login.

### 8. OAuth2 Flow (`oauth2-flow.mmd`)
Sequence diagram showing OAuth2 authorization code flow with biometric authentication.

### 9. Security Layers (`security-layers.mmd`)
Diagram showing the six layers of security in the system.

## Viewing Diagrams

### Online Viewers
- [Mermaid Live Editor](https://mermaid.live/)
- GitHub (automatically renders .mmd files)
- GitLab (automatically renders .mmd files)

### VS Code
Install the "Mermaid Preview" extension to view diagrams directly in VS Code.

### Command Line
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i diagram.mmd -o diagram.png
```

## Infrastructure as a Service (IaaS) Approach

The system is designed for IaaS deployment with:

- **Cloud-agnostic**: Works on AWS, GCP, Azure, or on-premise
- **Containerized**: Docker containers for easy deployment
- **Scalable**: Horizontal scaling with load balancers
- **Highly Available**: Multi-AZ deployment with replication
- **Self-hosted**: Full control over infrastructure and data
- **Kubernetes-ready**: Can be deployed on K8s clusters

## Key Design Decisions

### Why IaaS over SaaS?
1. **Data Sovereignty**: Full control over user data and credentials
2. **Customization**: Complete flexibility to modify and extend
3. **Cost Control**: No per-user pricing, predictable infrastructure costs
4. **Compliance**: Easier to meet regulatory requirements
5. **Security**: No third-party access to authentication data

### Architecture Principles
1. **Stateless Services**: API servers are stateless for easy scaling
2. **Separation of Concerns**: Clear boundaries between layers
3. **Defense in Depth**: Multiple security layers
4. **Fail-Safe Defaults**: Secure by default configuration
5. **Least Privilege**: Minimal permissions for all components
