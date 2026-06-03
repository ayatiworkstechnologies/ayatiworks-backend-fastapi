from locust import HttpUser, between, task


class BackendSmokeUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(3)
    def health(self):
        self.client.get("/health", name="GET /health")

    @task(2)
    def live(self):
        self.client.get("/health/live", name="GET /health/live")

    @task(1)
    def root(self):
        self.client.get("/", name="GET /")
