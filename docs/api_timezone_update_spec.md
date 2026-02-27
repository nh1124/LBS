# LBS API Timezone Update Specification (For External Integration Agents)

## 1. Overview
The Load Balancing System (LBS) API has been updated to support **Timezone-aware** tasks and scheduling.
This document outlines the API changes and required actions for external services, agents, and systems that integrate with the LBS API.

## 2. API Changes and New Specifications

### 1. Introduction of `X-Timezone` Request Header (Client Perspective)
A new header has been added for clients (apps, bots, external services) to inform the server **from which timezone the request is being made (i.e., which timezone the schedule should be calculated and displayed in)**.

- **Header Name**: `X-Timezone`
- **Value Format**: IANA Time Zone string (e.g., `Asia/Tokyo`, `Europe/Brussels`, `UTC`)
- **Default value**: If omitted, it will be treated as `UTC`.
- **Affected Endpoints**: All endpoints involving time-based calculations, such as `GET /schedule`, `GET /tasks/{id}/resolved`, `GET /dashboard`, `GET /heatmap`. The server will calculate date boundaries and return schedules based on the specified timezone.

### 2. Addition of `timezone` Field to Task Data (Absolute Task Time)
A new `timezone` field has been added to the task data model to define **the specific timezone in which a task is intended to be executed**.

- **Affected Endpoints**:
  - `POST /tasks` (Create Task)
  - `PUT /tasks/{id}` (Update Task)
- **New Field**: An IANA Time Zone string such as `"timezone": "Asia/Tokyo"`.
- **Specification**: This ensures that a `start_time` of `09:00:00` explicitly means "9:00 AM in Tokyo time" or "9:00 AM in New York time." When a client requests a schedule (using the `X-Timezone` header), the server will automatically calculate the time difference (shift) and return the appropriate localized time.

---

## 3. Changes to Python API Clients (`lbs_client.py` / `lbs_client_async.py`)
The officially provided Python API clients have been updated to automatically include the `X-Timezone` header.

### Addition of Argument to Initialization (Constructor)
By passing the `x_timezone` argument during instantiation, the `X-Timezone` header will be automatically added to all subsequent API requests.

**[Previous Usage]**
```python
client = LBSClient(api_key="your-api-key")
# All requests were processed based on UTC.
```

**[New Usage]**
```python
# Specify the execution environment's or user's specific timezone
client = LBSClient(api_key="your-api-key", x_timezone="Asia/Tokyo")

# From here on, methods like get_schedule() will fetch and convert data based on Tokyo time.
schedule = client.get_schedule(start_date="2026-02-27", end_date="2026-03-01")
```

---

## 4. Action Items for External Service Development Agents
For external integration services (bots, scripts, backend services, AI agents) using this API, please make the following modifications:

1. **Identify Timezone and Add Header**:
   - Determine the timezone environment (e.g., user settings or environment variables) for the user utilizing the service.
   - If making raw HTTP requests, ensure that the `X-Timezone: (User's Timezone)` header is added to every API request.
   - If using `LBSClient` / `AsyncLBSClient`, modify the initialization code to pass the timezone argument, such as `x_timezone="Asia/Tokyo"`.

2. **Modify Payload for Task Creation/Update**:
   - When creating or updating a task from an external service, if the task is meant to be executed based on a specific local time, ensure the JSON payload includes `"timezone": "(Target Timezone)"`.
   - If omitted, the server will register the task as `UTC`, which may cause unexpected time shifts when displayed to the user.

3. **Standardize Timezone Formatting**:
   - Always use the **IANA Time Zone Database format** (e.g., `Asia/Tokyo`, `America/New_York`) for timezone strings.
