# คู่มือติดตั้งและตั้งค่า Data Lakehouse Platform — PROD บน Portainer Stack

**Enterprise Data Lakehouse Platform · ฉบับ 2026-11-03**
**สถานะ: คู่มือสำหรับเตรียมการ deploy; ต้องผ่าน Production Readiness Gate และ human approval ก่อนใช้งานจริง**

> [!CAUTION]
> เอกสารนี้ครอบคลุมทั้ง **PROD Single Node** (ไม่มี HA) และ **PROD Multi-Host HA** (3 failure domains).
> ห้าม deploy จนกว่าจะผ่าน gate ครบและได้รับอนุมัติเป็นลายลักษณ์อักษร.
> การรัน containers หลายตัวบน host เดียว **ไม่ถือเป็น High Availability**.

---

## สารบัญ

| ส่วน | หัวข้อ |
|---:|---|
| 1 | [ภาพรวมสถาปัตยกรรม](#1-ภาพรวมสถาปัตยกรรม) |
| 2 | [ข้อกำหนดเบื้องต้น](#2-ข้อกำหนดเบื้องต้น) |
| 3 | [การเตรียม Host](#3-การเตรียม-host) |
| 4 | [การ Build และ Push Image](#4-การ-build-และ-push-image) |
| 5 | [การติดตั้ง Portainer Management Plane](#5-การติดตั้ง-portainer-management-plane) |
| 6 | [การจัดการ Secrets และ Environment Variables](#6-การจัดการ-secrets-และ-environment-variables) |
| 7 | [เส้นทาง A — PROD Single Node (ไม่มี HA)](#7-เส้นทาง-a--prod-single-node-ไม่มี-ha) |
| 8 | [เส้นทาง B — PROD Multi-Host HA (3 Failure Domains)](#8-เส้นทาง-b--prod-multi-host-ha-3-failure-domains) |
| 9 | [การตรวจรับหลังติดตั้ง](#9-การตรวจรับหลังติดตั้ง) |
| 10 | [Backup, Restore และ DR](#10-backup-restore-และ-dr) |
| 11 | [Monitoring และ Observability](#11-monitoring-และ-observability) |
| 12 | [Day-2 Operations](#12-day-2-operations) |
| 13 | [Rollback Procedures](#13-rollback-procedures) |
| 14 | [Production Readiness Gate Checklist](#14-production-readiness-gate-checklist) |
| 15 | [Handoff Contract](#15-handoff-contract) |

---
