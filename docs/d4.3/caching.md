# **High-Level Design: FastAPI-Based Data Transformation System with Caching**

## **1. Overview**

This document outlines the architecture and design decisions for a FastAPI-based system that retrieves large datasets (\~50MB) from external REST APIs, applies transformations, and serves the processed data efficiently. The system is deployed on **Kubernetes (k8s)** using **ArgoCD** and **Kustomize**, with potential federation across multiple clusters.

## **2. System Components**

### **FastAPI Services**

- Each FastAPI service retrieves data from a unique external API and applies service-specific transformations.
- Services are dynamically created and removed, requiring a scalable and adaptable deployment model.

### **Caching Layer**

- Used to improve performance and reduce redundant data retrieval.
- Two caching options were considered:
  - **DiskCache**: Suitable for a single FastAPI instance.
  - **Redis**: Preferred for multiple services in a shared cluster.
- **Final Choice**: **Redis** (single shared instance for multiple services).

### **Deployment Infrastructure**

- **Kubernetes (k8s)** for container orchestration.
- **ArgoCD** for GitOps-based CI/CD pipeline.
- **Kustomize** for managing environment-specific configurations.
- **Potential Cluster Federation** to manage multi-cluster deployments.

---

## **3. Caching Strategy**

### **3.1 Cache Key Structure**

To avoid conflicts across multiple services and datasets, cache keys follow this structured format:

```
{SERVICE_NAME}:{DATA_TYPE}:{ENDPOINT}
```

- **SERVICE\_NAME** → Identifies the FastAPI instance.
- **DATA\_TYPE** → Distinguishes between **original** vs. **transformed** data.
- **ENDPOINT** → Supports multiple API endpoints per service.

### **3.2 Cache Expiry and Cleanup**

- **TTL-based Expiry (**\`\`**)**: Each cache entry automatically expires after a defined period (e.g., 5 minutes).
- **Periodic Cleanup**: If necessary, a background process can remove stale cache data from services no longer in use.

### **3.3 Data Freshness Mechanisms**

To ensure the cached data remains fresh:

1. **ETag / Last-Modified Headers** (if supported by external API):
   - Stored with cached data.
   - Sent in subsequent requests via `If-None-Match` / `If-Modified-Since`.
   - If response is `304 Not Modified`, use cached data.
2. **Version Check API** (alternative if headers are unavailable):
   - Queries a lightweight endpoint (e.g., `/version`).
   - Compares response with the cached version before fetching a full dataset.

---

## **4. Deployment Considerations**

### **4.1 Redis Deployment**

**Decision:** Use a single **shared Redis instance** for multiple FastAPI services.

- **Option 1: Redis as a Sidecar in Each Pod** (❌ Rejected)
  - Pros: Data is local to each FastAPI instance.
  - Cons: Cache is lost when the pod restarts.
- **Option 2: Redis as a Separate k8s Deployment** (✅ Chosen)
  - Pros: Shared cache across services, survives pod restarts.
  - Cons: Requires network calls but is manageable.

### **4.2 Service Scalability & Federation**

- FastAPI services are dynamically created and removed.
- Potential deployment across **multiple federated clusters**.
- **Redis clustering or separate Redis instances per cluster** might be needed for cross-cluster caching.

### **4.3 ArgoCD & Kustomize Integration**

- **ArgoCD** ensures GitOps-based automated deployments.
- **Kustomize** helps manage service-specific configurations (e.g., environment-specific Redis connections, different external API endpoints).

---

## **5. Summary of Key Design Decisions**

| **Component**         | **Decision**                                                        | **Reasoning**                                  |
| --------------------- | ------------------------------------------------------------------- | ---------------------------------------------- |
| **Caching Strategy**  | **Redis (shared instance)**                                         | Needed for multiple services in k8s.           |
| **Cache Keying**      | `{SERVICE_NAME}:{DATA_TYPE}:{ENDPOINT}`                             | Ensures namespace isolation.                   |
| **Cache Expiry**      | `SETEX` (TTL-based expiry)                                          | Simple, automatic cleanup.                     |
| **Freshness Check**   | `ETag` / `Last-Modified` if available, otherwise version check API  | Ensures data validity without full fetch.      |
| **Redis Deployment**  | **Separate k8s deployment**                                         | Shared cache, survives pod restarts.           |
| **Deployment Method** | **ArgoCD + Kustomize**                                              | GitOps-based CI/CD, flexible configuration.    |
| **Cluster Strategy**  | **Potential federation** (multiple clusters with service discovery) | Scalability, resilience, cross-region support. |

---

## **6. Next Steps**

- Implement Redis-backed caching in FastAPI services.
- Integrate freshness checks using HTTP headers or version requests.
- Set up ArgoCD & Kustomize for automated deployments.
- Evaluate cross-cluster Redis strategy if needed.

Would you like me to refine this further or add any additional details? 🚀

