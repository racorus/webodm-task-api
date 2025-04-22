# WebODM Task Ownership API

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.85-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

A small FastAPI service to inspect WebODM tasks, their owners, and user access.  
It connects to your WebODM PostgreSQL database, queries task/project/permission tables, and exposes JSON endpoints for:

- Listing tasks with ownership & processing info  
- Listing task statuses  
- Fetching the owner of a specific task  
- Checking whether a given user can access a task

---

## Table of Contents

1. [Features](#features)  
2. [Requirements](#requirements)  
3. [Installation](#installation)  
4. [Configuration](#configuration)  
5. [Running the Service](#running-the-service)  
6. [API Endpoints](#api-endpoints)  
7. [Examples](#examples)  
8. [Contributing](#contributing)  
9. [License](#license)  

---

## Features

- 🗂  **Task Ownership**: List all tasks and infer the “owner” by permission count  
- 📊  **Task Statuses**: View processing status codes & names  
- 👤  **Owner Lookup**: Get the single most likely owner for any task  
- 🔒  **Access Check**: Determine if a user (or group) may view a task  

---

## Requirements

- Python 3.9 or higher  
- PostgreSQL (as used by WebODM)  
- A copy of your WebODM database credentials  

---

## Installation

1. **Clone the repo**  
   ```bash
   git clone https://github.com/racorus/webodm-task-api.git
   cd webodm-task-api
