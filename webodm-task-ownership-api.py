from fastapi import FastAPI, Depends, HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
import uvicorn
from datetime import datetime, timezone


# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="WebODM Task Ownership API",
    description="API for checking task ownership and permissions in WebODM",
    version="1.0.0"
)

# Database connection parameters from environment variables
DB_PARAMS = {
    "dbname": os.getenv("DB_NAME", "webodm_dev"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "host": os.getenv("DB_HOST", "db"),
    "port": os.getenv("DB_PORT", "5432"),
}

def get_db_connection():
    """Establish a connection to the PostgreSQL database"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

class TaskPermission(BaseModel):
    task_id: int
    task_uuid: str
    task_name: str
    project_id: int
    project_name: str
    owner_username: str
    permissions: str
    permission_count: int
    group_memberships: Optional[str] = None

class TaskOwnershipResponse(BaseModel):
    tasks: List[TaskPermission]
    
class TaskStatus(BaseModel):
    status_code: int
    status_name: str
    
def get_task_status_map():
    """Returns a mapping of status codes to human-readable status names"""
    return {
        10: "QUEUED",
        20: "RUNNING",
        30: "FAILED",
        40: "COMPLETED",
        50: "CANCELED"
    }

@app.get("/")
def read_root():
    return {
        "message": "WebODM Task Ownership API",
        "endpoints": [
            "/api/tasks/ownership",
            "/api/tasks/status",
            "/api/tasks/{task_id}/owner",
            "/api/tasks/{task_id}/check-access/{username}"
        ]
    }


@app.get("/api/tasks/ownership")
def get_task_ownership():
    """Get all tasks with their ownership information including processing date and days elapsed"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT 
            t.id AS task_id,
            t.uuid AS task_uuid,
            t.name AS task_name,
            t.created_at AS processing_date,
            t.status AS task_status,
            p.id AS project_id,
            p.name AS project_name,
            u.username AS probable_owner,
            COUNT(DISTINCT perm.codename) AS permission_count,
            string_agg(DISTINCT perm.codename, ', ') AS permissions,
            string_agg(DISTINCT g.name, ', ') AS group_memberships
        FROM 
            app_task t
        JOIN 
            app_project p ON t.project_id = p.id
        JOIN 
            app_projectuserobjectpermission puop ON puop.content_object_id = p.id
        JOIN 
            auth_user u ON puop.user_id = u.id
        JOIN 
            auth_permission perm ON puop.permission_id = perm.id
        LEFT JOIN
            auth_user_groups ug ON u.id = ug.user_id
        LEFT JOIN
            auth_group g ON ug.group_id = g.id
        GROUP BY 
            t.id, t.uuid, t.name, t.created_at, t.status, p.id, p.name, u.username
        HAVING 
            COUNT(DISTINCT perm.codename) >= 4  -- Users with all permissions are likely owners
        ORDER BY 
            t.id, permission_count DESC;
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        status_map = get_task_status_map()
        current_time = datetime.now(timezone.utc)
        
        # Add status name and days elapsed to each task
        for task in results:
            task["status_name"] = status_map.get(task["task_status"], f"Unknown ({task['task_status']})")
            
            # Calculate days elapsed since processing
            if task["processing_date"]:
                process_date = task["processing_date"]
                if isinstance(process_date, str):
                    process_date = datetime.fromisoformat(process_date.replace('Z', '+00:00'))
                
                elapsed = current_time - process_date
                task["days_since_processed"] = elapsed.days
            else:
                task["days_since_processed"] = None
        
        return {"tasks": results}
    
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    finally:
        if conn:
            conn.close()


@app.get("/api/tasks/status")
def get_task_status():
    """Get all tasks with their processing status"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT 
            t.id AS task_id,
            t.uuid AS task_uuid,
            t.name AS task_name,
            t.status AS task_status,
            p.id AS project_id,
            p.name AS project_name,
            u.username AS owner_username
        FROM 
            app_task t
        JOIN 
            app_project p ON t.project_id = p.id
        JOIN 
            app_projectuserobjectpermission puop ON puop.content_object_id = p.id
        JOIN 
            auth_user u ON puop.user_id = u.id
        JOIN 
            auth_permission perm ON puop.permission_id = perm.id
        GROUP BY 
            t.id, t.uuid, t.name, t.status, p.id, p.name, u.username
        HAVING 
            COUNT(DISTINCT perm.codename) >= 4  -- Users with all permissions are likely owners
        ORDER BY 
            t.id;
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        status_map = get_task_status_map()
        
        # Add status name to each task
        for task in results:
            task["status_name"] = status_map.get(task["task_status"], f"Unknown ({task['task_status']})")
        
        return {"tasks": results}
    
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    finally:
        if conn:
            conn.close()

@app.get("/api/tasks/{task_id}/owner")
def get_task_owner(task_id: int):
    """Get the owner of a specific task"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT 
            t.id AS task_id,
            t.uuid AS task_uuid,
            t.name AS task_name,
            t.status AS task_status,
            p.id AS project_id,
            p.name AS project_name,
            u.username AS owner_username,
            string_agg(DISTINCT perm.codename, ', ') AS permissions,
            string_agg(DISTINCT g.name, ', ') AS group_memberships
        FROM 
            app_task t
        JOIN 
            app_project p ON t.project_id = p.id
        JOIN 
            app_projectuserobjectpermission puop ON puop.content_object_id = p.id
        JOIN 
            auth_user u ON puop.user_id = u.id
        JOIN 
            auth_permission perm ON puop.permission_id = perm.id
        LEFT JOIN
            auth_user_groups ug ON u.id = ug.user_id
        LEFT JOIN
            auth_group g ON ug.group_id = g.id
        WHERE
            t.id = %s
        GROUP BY 
            t.id, t.uuid, t.name, t.status, p.id, p.name, u.username
        HAVING 
            COUNT(DISTINCT perm.codename) >= 4  -- Users with all permissions are likely owners
        ORDER BY 
            COUNT(DISTINCT perm.codename) DESC
        LIMIT 1;
        """
        
        cursor.execute(query, (task_id,))
        result = cursor.fetchone()
        
        if result is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found or has no owner")
        
        # Add status name
        status_map = get_task_status_map()
        result["status_name"] = status_map.get(result["task_status"], f"Unknown ({result['task_status']})")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    finally:
        if conn:
            conn.close()

@app.get("/api/tasks/{task_id}/check-access/{username}")
def check_user_access_to_task(task_id: int, username: str):
    """Check if a specific user has access to a task"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT 
            t.id AS task_id,
            t.name AS task_name,
            t.status AS task_status,
            p.id AS project_id,
            p.name AS project_name,
            p.public AS is_public,
            u.username,
            u.is_superuser,
            string_agg(DISTINCT perm.codename, ', ') AS direct_permissions,
            string_agg(DISTINCT g.name, ', ') AS user_groups
        FROM 
            app_task t
        JOIN 
            app_project p ON t.project_id = p.id
        JOIN 
            auth_user u ON u.username = %s
        LEFT JOIN
            app_projectuserobjectpermission puop ON puop.content_object_id = p.id AND puop.user_id = u.id
        LEFT JOIN
            auth_permission perm ON puop.permission_id = perm.id
        LEFT JOIN
            auth_user_groups ug ON u.id = ug.user_id
        LEFT JOIN
            auth_group g ON ug.group_id = g.id
        WHERE
            t.id = %s
        GROUP BY 
            t.id, t.name, t.status, p.id, p.name, p.public, u.username, u.is_superuser;
        """
        
        cursor.execute(query, (username, task_id))
        result = cursor.fetchone()
        
        if result is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} or user {username} not found")
        
        # Also fetch group permissions for this project
        group_query = """
        SELECT 
            g.name AS group_name,
            string_agg(DISTINCT perm.codename, ', ') AS group_permissions
        FROM 
            app_task t
        JOIN 
            app_project p ON t.project_id = p.id
        JOIN 
            app_projectgroupobjectpermission pgop ON pgop.content_object_id = p.id
        JOIN 
            auth_group g ON pgop.group_id = g.id
        JOIN 
            auth_permission perm ON pgop.permission_id = perm.id
        WHERE
            t.id = %s AND g.name IN (
                SELECT g.name FROM auth_user u
                JOIN auth_user_groups ug ON u.id = ug.user_id
                JOIN auth_group g ON ug.group_id = g.id
                WHERE u.username = %s
            )
        GROUP BY 
            g.name;
        """
        
        cursor.execute(group_query, (task_id, username))
        group_results = cursor.fetchall()
        
        # Determine access level
        has_access = False
        access_type = []
        
        if result['is_superuser']:
            has_access = True
            access_type.append("superuser")
        
        if result['is_public']:
            has_access = True
            access_type.append("public project (view)")
        
        if result['direct_permissions'] and 'view_project' in result['direct_permissions']:
            has_access = True
            access_type.append(f"direct permissions: {result['direct_permissions']}")
        
        group_permissions = []
        for group in group_results:
            if 'view_project' in group['group_permissions']:
                has_access = True
                group_permissions.append(f"{group['group_name']}: {group['group_permissions']}")
        
        if group_permissions:
            access_type.append(f"group permissions: {', '.join(group_permissions)}")
        
        # Add status name
        status_map = get_task_status_map()
        result["status_name"] = status_map.get(result["task_status"], f"Unknown ({result['task_status']})")
        
        return {
            "task_id": result["task_id"],
            "task_name": result["task_name"],
            "task_status": result["task_status"],
            "status_name": result["status_name"],
            "project_id": result["project_id"],
            "project_name": result["project_name"],
            "username": username,
            "is_superuser": result["is_superuser"],
            "has_access": has_access,
            "access_type": access_type if access_type else ["no access"],
            "user_groups": result["user_groups"],
            "is_public_project": result["is_public"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print(f"Starting WebODM Task Ownership API")
    print(f"Database connection parameters: {DB_PARAMS}")
    uvicorn.run(app, host="0.0.0.0", port=8080)
