# tools/cloud/k8s/clusters/

One module a provider: everything the Kubernetes job path asks of a cloud (make, cap and delete the cluster and
its class pools, its nodes with their billed times, prices, the month's bill). The interface is in `../CLAUDE.md`
("Another provider"); `scaleway.py` (Kapsule) is the first and its docstring holds Scaleway's facts.

- **Find the cluster by its project's name and its own name; check its own project id** before changing or
  deleting it. The Scaleway organisation holds another company's cluster in another project: never list
  organisation-wide, never touch it.
- **Nothing project-specific in the repo:** no project, cluster or pool ids, no kubeconfig. The kubeconfig is
  written to `~/.farm-factory-props/cloud/kubeconfig-<cluster>.yaml` (mode 600).
- A module here shares its name with the provider's backend (`tools/props/cloud/backends/`); load it by path
  (`../submitter.py` `cluster_module`), never by `import <provider>`.
- Pools start at max 0; `cap_pools` sets each max from the month's euros left, and `idle` sets all to 0.
