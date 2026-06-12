from aiokafka import AIOKafkaProducer

from app.workers.kafka_manager import kafka_manager
from app.workers.models import SpringFixKafka, SpringFixResult


async def produce_spring_fix_event(spring_fix_kafka:SpringFixKafka):
    kafka_producer_ : AIOKafkaProducer = kafka_manager.producer
    await kafka_producer_.send_and_wait("spring_fix", spring_fix_kafka.model_dump_json().encode("utf-8"))

async def produce_spring_fix_result(spring_fix_result:SpringFixResult):
    kafka_producer_ : AIOKafkaProducer = kafka_manager.producer
    await kafka_producer_.send_and_wait("spring_fix_result", spring_fix_result.model_dump_json().encode("utf-8"))