from typing import Dict
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

PUSHGATEWAY_ADDR = "prometheus-pushgateway:9091"

def push_generation_metrics(gen_metrics: Dict[str, float], job_name: str = "rag_generation_eval"):
    """
    gen_metrics example:
      {"faithfulness": 0.85, "context_precision": 0.9, ...}
    """
    registry = CollectorRegistry()

    for key, value in gen_metrics.items():
        metric_name = f"rag_generation_{key}"
        g = Gauge(metric_name, f"RAG generation metric {key}", registry=registry)
        g.set(value)

    push_to_gateway(PUSHGATEWAY_ADDR, job=job_name, registry=registry)