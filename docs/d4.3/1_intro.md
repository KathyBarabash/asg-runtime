# Final Report for WP4 of the TEADAL Project

## Introduction

According to the overarching TEADAL architecture (*todo: add references to WP2 deliverables*), **Federated Data Products (FDPs)** are owned and maintained by specific domains or teams within each organization participating in the TEADAL Federation. While this model respects data ownership and leverages domain expertise within individual organizations, directly exposing FDPs for cross-organizational sharing introduces challenges.

These challenges primarily concern two aspects:
- **Trust and privacy**, particularly across organizational boundaries between data owners and data consumers;
- **Efficiency and control** of infrastructure and data flow across the federation.

To address these limitations, the TEADAL architecture introduces the concept of **Shared Federated Data Products (SFDPs)**. An SFDP provides controlled access to underlying FDPs, operating under the governance of the TEADAL platform. This approach ensures that all aspects of the data-sharing agreement — including privacy, policy, and transformation requirements — are enforced at the interface level.

### Business-Level Motivations for SFDPs

- Facilitate internal data-sharing agreements without altering source systems;
- Provide versioning, governance, and traceability for reused data flows;
- Act as policy-compliant "middleware" between consumers and FDPs;
- Reduce time-to-data and development effort for data consumers.

### System-Level Objectives of SFDPs

- Enforce data-sharing contracts at the API level;
- Apply required data transformations and policies before exposure;
- Preserve auditable boundaries between data ownership and consumption;
- Decouple consumers from the technical and semantic complexity of data sources;
- Represent transformed/contractual APIs as reusable, discoverable data products.

In this deliverable, we present the final design of the key technical components supporting the SFDP concept as part of the **TEADAL Stretched Data Lake**. We demonstrate how the SFDP layer enhances the federation’s data-sharing capabilities in alignment with the TEADAL architecture. This includes the end-to-end process: from SFDP negotiation and specification to its automated creation, deployment, and lifecycle management across the TEADAL Federation — all designed to meet both contractual and optimization objectives.

*todo: Insert overview of the report structure with section references when finalized.*
