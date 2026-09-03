# ADR-0004: ClickHouse Keeper Coordination for High Availability

## Status
Accepted

## Context
ClickHouse replication (`ReplicatedMergeTree`) and distributed DDL execution (`ON CLUSTER`) require a centralized, highly reliable distributed consensus service. Historically, Apache ZooKeeper was used, which required an external JVM runtime, substantial memory overhead, and separate operational tooling.

## Decision
1. Standardize on **ClickHouse Keeper** as the consensus coordination engine, replacing external ZooKeeper.
2. In production HA, deploy a **3-node Keeper Raft quorum** distributed across 3 independent physical hosts / failure domains:
   - Host 1: ClickHouse Replica 1 + Keeper Member 1
   - Host 2: ClickHouse Replica 2 + Keeper Member 2
   - Host 3: Keeper Member 3 (Tie-breaker node to maintain odd-numbered Raft quorum)
3. Keeper instances will communicate over dedicated internal ports (9181 for client requests, 9234 for Raft peer consensus) and remain isolated from external client networks.

## Consequences
### Positive
- Fully native C++ implementation without Java/JVM runtime overhead or JVM garbage collection pauses.
- Lower memory consumption and operational uniformity with ClickHouse server binaries.
- Compatible with ZooKeeper wire protocol, allowing native drop-in interaction.

### Negative / Trade-offs
- Requires careful network partition and quorum management (loss of 2 out of 3 nodes halts replication and DDL mutations until quorum is restored).
