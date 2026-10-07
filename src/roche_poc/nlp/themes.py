"""(Empty, future work) Sub-themes inside a root cause.

Planned approach: embed the English comments (``nomic-embed-text-v1.5`` served by LM
Studio, so no new cloud dependency), cluster them inside one root cause (e.g.
``S_Machine/Capacity Issues`` -> strike / breakdown / staff shortage) and let the LLM
*name* each cluster. Evaluate clusters with silhouette score and manual inspection.
"""


def cluster_comments(*args, **kwargs):
    raise NotImplementedError("Planned for a later development phase (see docs/architecture.md).")
