class ModelServingService:
    """Loads approved predictive-maintenance models and serves predictions."""

    def predict_failure(
        self,
        observation: dict[str, object],
        request_id: str | None = None,
    ) -> dict[str, object]:
        return {
            "status": "not_configured",
            "failure_probability": None,
            "risk_class": None,
            "model_version": None,
            "message": (
                "Model serving is ready to be implemented. "
                "The next step is training a classifier and loading the approved MLflow model."
            ),
            "metadata": {
                "request_id": request_id,
                "received_observation": observation,
                "target": "Machine failure",
            },
        }


def get_model_serving_service() -> ModelServingService:
    return ModelServingService()
