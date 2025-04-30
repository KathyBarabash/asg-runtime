## Stretched Data Lakes Summary

While the concept of Shared Federated Data Products (SFDPs) was introduced to enable trusted cross-organizational data sharing, it also offers an opportunity to address the infrastructure-related challenges that would arise from exposing Federated Data Products (FDPs) directly. As part of our work on the TEADAL Stretched Data Lakes and its Control Plane, we have leveraged this opportunity to develop a complete toolchain for the creation and lifecycle management of SFDPs.

Our solution enables SFDPs to be implemented as lightweight, self-contained API services that act as controlled intermediaries between FDPs and their consumers. These SFDPs are generated using a templated application framework, backed by a shared runtime library. This approach facilitates rapid development, consistent deployment, and unified runtime management of SFDPs across the TEADAL Federation.

The benefits of this approach include:

- **Developer Efficiency**: Minimal boilerplate and low barrier to entry accelerate the creation of SFDPs.
- **Structural Uniformity**: All SFDPs follow a standardized layout and operational model.
- **Observability and Control**: Built-in instrumentation, caching, and transformation logic ensure robust monitoring and control.
- **Governability**: All interface and behavior definitions are derived from declarative specifications.

This unified lifecycle for SFDP generation and operation transforms them into advanced, policy-aware data pipelines. These pipelines:

- Retrieve data from source FDPs,
- Apply required transformations,
- Optionally cache raw and computed outputs,
- And expose the data to users under strict runtime policies and trust guarantees — the same guarantees that apply to FDPs.

All of this operates under the control of the TEADAL Control Plane, which leverages smart telemetry, declarative policy, and dynamic optimization.

---

### Stretched Data Lakes in the TEADAL Architecture

*todo – briefly summarize the major functionality (data-driven performance/deployment management) and components, possibly with diagram*

#### Functional Responsibilities and Components

*todo – Stretched Data Lakes componentry is responsible for data-related infrastructure and operational enablement within the TEADAL architecture.*

---

### Catalog Flows for SFDP Creation (CERFIEL)

*todo – Alessio to describe how the catalog supports the SFDP creation process, ideally with screenshots.*

---

### Stretched Data Lakes in the TEADAL Platform

To make the TEADAL Node capable and production-ready, a range of enabling technologies have been integrated. This includes:

- **GitLab CI/CD and Argo CD** for GitOps-driven automation,
- **OPA (Open Policy Agent), Rego, and Keycloak** for fine-grained policy enforcement and secure identity management,
- **Prometheus, Thanos, Kepler, and Grafana** for federated observability and resource monitoring.

The Stretched Data Lakes components have been designed to be compatible with this curated TEADAL technology stack. Whenever feasible, they are integrated with the foundational services of the TEADAL Node, extending them where necessary.

*todo – Briefly summarize integration status of each component into the TEADAL Node (e.g., platform-infra vs. platform-apps, optional vs. required, dependencies, etc.), possibly using a diagram or a reference table.*

---

### Stretched Data Lakes Services for the TEADAL Pilots

*todo – Provide a table summarizing which pilots make use of which components, highlighting any pilot-specific extensions or adaptations.*

---

### Stretched Data Lakes and TEADAL KPIs

The Stretched Data Lakes approach directly supports several TEADAL KPIs and pilot use cases. Examples include:

1. **KPI 1.2 / KPI 1.3 — Data Product Adoption**  
   By monitoring the creation and usage of SFDPs across the federation, we gather insights into adoption trends and identify opportunities to foster reuse.

2. **KPI 3.1 / KPI 3.2 — Resource Efficiency**  
   Our telemetry system tracks storage and network usage for each SFDP, enabling automated or operator-guided decisions to optimize infrastructure use.

3. **Performance and Trust Constraints**  
   The SFDP deployment framework supports targeted placement strategies — for example, on GPU-enabled or TEE-secured nodes — allowing the system to meet application-specific performance or trust requirements.

