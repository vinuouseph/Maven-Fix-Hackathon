from aiokafka import AIOKafkaProducer


class KafkaManager:
    def __init__(self):
        self.producer: AIOKafkaProducer | None = None

kafka_manager = KafkaManager()