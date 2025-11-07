import psutil
import socket

def manage_port_process(port):
    """
    Find and terminate processes running on a specified port
    Returns tuple of (found_process, success)
    """
    for proc in psutil.process_iter(['pid', 'name', 'net_connections']):
        try:
            # Get connections for this process
            connections = proc.net_connections()
            for conn in connections:
                if conn.laddr.port == port:
                    print(f"Found process using port {port}:")
                    print(f"PID: {proc.pid}")
                    print(f"Name: {proc.name()}")
                    
                    # Attempt to terminate gracefully
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)  # Wait for graceful shutdown
                        return True, f"Successfully terminated process {proc.pid}"
                    except psutil.TimeoutExpired:
                        # Force kill if graceful shutdown fails
                        proc.kill()
                        return True, f"Force killed process {proc.pid}"
                        
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
            
    return False, "No process found on port 2000"

# Example usage
success, message = manage_port_process(2000)
print(message)