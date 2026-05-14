from sqlalchemy import Column, Integer, Float, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base

class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    cpu_percent = Column(Float)
    cpu_freq_mhz = Column(Float)
    memory_percent = Column(Float)
    memory_used_gb = Column(Float)
    memory_available_gb = Column(Float)
    swap_percent = Column(Float)
    swap_used_gb = Column(Float)
    disk_read_mb = Column(Float)
    disk_write_mb = Column(Float)
    disk_percent = Column(Float)
    net_sent_mb = Column(Float)
    net_recv_mb = Column(Float)
    load_avg_1 = Column(Float)
    load_avg_5 = Column(Float)
    load_avg_15 = Column(Float)
    io_wait = Column(Float, nullable=True)

class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    bench_type = Column(String(50))   # cpu | memory | disk
    tool = Column(String(50))         # sysbench | fio | stress-ng
    duration_sec = Column(Integer)
    result_json = Column(Text)        # raw parsed output as JSON string
    summary = Column(Text)            # human-readable summary

class BottleneckEvent(Base):
    __tablename__ = "bottleneck_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    resource = Column(String(50))     # cpu | memory | disk | swap | load
    severity = Column(String(20))     # warning | critical
    message = Column(Text)
    value = Column(Float)
