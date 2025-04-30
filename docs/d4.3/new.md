TEADAL: Realizing Controlled and Composable Federated Data Flows

The TEADAL project aims to support secure, policy-driven data sharing across organizational boundaries by enabling the creation and operation of Federated Data Products (FDPs). Through a modular architecture, TEADAL empowers organizations to expose and consume data while maintaining control over infrastructure, policies, and access — forming dynamic federations of trust.

While the TEADAL platform encompasses a wide array of capabilities — from architectural frameworks (WP2) to policy modeling (WP3), trust enforcement (WP5), and DevOps automation (WP6) — this report presents the outcomes and insights specifically from WP4, which addresses the realization and control of federated data flows.

Originally conceived under the term “stretched data lakes,” WP4 evolved throughout the project into a broader technical stream concerned with building, deploying, and managing actual data flow pipelines across federation participants. This work included the design and implementation of tools, runtime components, and deployment models that enable secure composition, transformation, and delivery of shared data products, often across heterogeneous infrastructure.

Our work draws on and complements key architectural concepts defined in WP2 (e.g., the Shared FDP or sFDP pattern), and is closely integrated with GitOps-based tooling and cluster lifecycle management from WP6 (e.g., the TEADAL Node Base Repo).

The remainder of this report introduces and explains the main components and tools developed in WP4, such as the ASG Toolkit, the ASG Runtime, and the ASG-sFDP Server. We also reflect on how these tools operationalize the TEADAL vision in practical deployments, and discuss future directions and applications that can extend this work into research, education, and industrial settings.

---
## Executive Summary

The TEADAL project empowers organizations to securely collaborate on data-driven tasks across distributed infrastructures. It introduces a novel architecture for federated data sharing, allowing participating organizations to contribute, transform, and consume datasets without centralizing sensitive information. Key to this architecture is the concept of Federated Data Products (FDPs), which serve as shareable REST endpoints exposing organizational data, and Shared Federated Data Products (sFDPs), which enable re-exposure of external FDPs under controlled conditions. This architecture is implemented using Kubernetes-based deployments and GitOps practices to maintain consistency and security across the federation.

This document reports on the work of **Work Package 4 (WP4)** within the TEADAL project. WP4 focuses specifically on realizing and managing cross-organizational data flows, originally conceptualized as "stretched data lakes" and evolved over time into a more modular and runtime-oriented architecture. The contributions described here include design, prototyping, and tooling that together allow federated data pipelines to be declaratively specified, consistently deployed, and programmatically observed. These results directly support the broader architectural goals of TEADAL and provide practical mechanisms to implement and govern data flows as part of shared infrastructures.

## TEADAL Infrastructure and Deployment Model

Within the TEADAL architecture, each participating organization may host its own infrastructure segment known as a **TEADAL Infrastructure**. These segments are independent Kubernetes clusters backed by a GitOps workflow using ArgoCD and Kustomize. To ensure consistency and encourage best practices across installations, a shared template called the **TEADAL Node Base Repo** provides a common foundation for deployment and configuration.

Each TEADAL Infrastructure acts as a deployment target for data products (FDPs and sFDPs), data transformations, and supporting services. By managing these through Git repositories and declarative manifests, TEADAL aligns with modern cloud-native practices and offers flexibility for real-world organizational constraints.

## TEADAL Platform Components from WP4

Work Package 4 developed three main software components that together form the TEADAL runtime system for data flows:

- **ASGT Tool**: A command-line utility that transforms declarative pipeline definitions (MultiClusterApp YAML) into deployment-ready assets for one or more clusters.
- **ASG Runtime**: A controller running in a central observability cluster that continuously tracks the status of data pipeline deployments across the federation.
- **ASG-sFDP**: A service component that implements the logic of a Shared Federated Data Product, consuming external FDPs and re-exposing transformed outputs via REST APIs.

All three components rely on a common low-level GitOps interaction library called **Gin**, which abstracts away Git provider specifics and repository structures.

### Deployment Flow

1. A federation-wide pipeline is defined using the `TeadalPipeline` CRD.
2. The ASGT Tool interprets this and writes per-cluster deployment artifacts into corresponding Git repositories.
3. ArgoCD agents running in each cluster detect these changes and deploy the components accordingly.
4. The ASG Runtime polls the clusters to collect deployment statuses and updates a shared status view.
5. ASG-sFDP services are deployed where needed to re-expose downstream outputs based on upstream FDPs.

## Value and Benefits

The WP4 work makes several important contributions:

- **Modular Runtime Architecture**: By cleanly separating tooling (ASGT), runtime observability (ASG), and service endpoints (ASG-sFDP), the system supports reuse, substitution, and independent evolution of each part.
- **Automation and Governance**: GitOps integration ensures that all deployments are reproducible, auditable, and observable.
- **Declarative Federation**: Federated pipelines are treated as high-level artifacts that can be declaratively defined and then automatically deployed across a multi-cluster environment.

These features directly support TEADAL’s goals of trust, autonomy, and control in federated data sharing.

## Terminology and Consistency

To clarify project-specific terminology:

- **TEADAL**: The name of the research project.
- **TEADAL Platform**: The project’s technical outcome enabling cross-organization data sharing.
- **TEADAL Infrastructure**: A Kubernetes-based deployment segment run by one organization.
- **TEADAL Node Base Repo**: A common GitOps configuration template for deploying TEADAL Infrastructure.
- **FDP / sFDP**: Data products exposed as REST endpoints (original or re-exposed, respectively).
- **ASGT / ASG / ASG-sFDP / Gin**: The WP4-developed components that support deployment and execution of data flows.

## Future Evolution and Community Models

The work presented here forms the foundation for continued evolution:

- **Industry Partners** may incorporate these capabilities into product lines or services.
- **Research Organizations** gain a real-world implementation platform to explore new federated data paradigms.
- **Educational Partners** can train the next generation of cloud-native data engineers.
- **Use-Case Owners** benefit from tangible assets that can be extended into market-ready offerings.

Different community models may emerge around these roles: vendor-led open source, academic-led consortia, or hybrid models involving both proprietary and open extensions. Each model will tailor the project assets to their stakeholders' needs and capabilities.

In addition, the WP4 infrastructure has potential alignment with the **MCP (Multi-Cluster Platform)** trend, where decentralized deployment and control of software components across federated clusters is becoming increasingly important. TEADAL’s GitOps-driven approach to federation may serve as a reference model or early prototype of MCP-aligned architectures.

## Outstanding TODOs

- A detailed figure showing the relationship between ASGT, ASG Runtime, ASG-sFDP, and Gin is forthcoming.
- A table or diagram mapping GitOps roles to deployment targets per cluster is under development.
- Further documentation on Gin’s abstraction model and how it bridges Git providers is in progress.

## References

(*To be completed*)

