import uvicorn
import argparse

def main():
    parser = argparse.ArgumentParser(description='Run Sublet Backend Server')
    parser.add_argument('--host', type=str, default='127.0.0.1',
                      help='Host to run the server on')
    parser.add_argument('--port', type=int, default=8000,
                      help='Port to run the server on')
    parser.add_argument('--reload', action='store_true',
                      help='Enable auto-reload for development')
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main() 