# Greenhouse Control Project

This project is a web application to monitor and control a greenhouse environment using a Raspberry Pi. It features a FastAPI backend and a React frontend.

## Project Structure

- `api/`: The FastAPI backend application.
- `client/`: The React frontend application.
- `legacy/`: The original Django project code.

---

## Running the Application

You can run the application either manually or using Docker Compose.

### Manual Setup (for Development on Raspberry Pi)

#### 1. Setup PostgreSQL Database

-   Ensure PostgreSQL is installed and running.
-   Create a new database and user. Using `psql`:

    ```bash
    sudo -u postgres psql
    CREATE DATABASE greenhousedb;
    CREATE USER user WITH PASSWORD 'password'; -- Replace with your own credentials
    GRANT ALL PRIVILEGES ON DATABASE greenhousedb TO user;
    \q
    ```
-   **Important:** Update the `SQLALCHEMY_DATABASE_URL` in `api/database.py` with your PostgreSQL credentials if you are not using Docker.

#### 2. Run the Backend (FastAPI)

-   Navigate to the `api` directory:
    ```bash
    cd api
    ```
-   Create a virtual environment and install dependencies:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
-   Run the application:
    ```bash
    uvicorn main:app --reload
    ```
-   The backend will be available at `http://127.0.0.1:8000`. API documentation is at `http://127.0.0.1:8000/docs`.

#### 3. Run the Frontend (React)

-   Open a new terminal window.
-   Navigate to the `client` directory:
    ```bash
    cd client
    ```
-   Install dependencies:
    ```bash
    npm install
    ```
-   Run the application:
    ```bash
    npm start
    ```
-   The frontend will be available at `http://localhost:3000`.

---

### Docker Compose Setup (Recommended)

This is the easiest way to get the entire application stack running.

#### Prerequisites
-   [Docker](https://docs.docker.com/engine/install/) installed.
-   [Docker Compose](https://docs.docker.com/compose/install/) installed.

#### Running
1.  From the project root directory (`greenhouse`), run the following command:
    ```bash
    docker-compose up --build
    ```
2.  The application will be available at `http://localhost`.
    -   The React frontend is served on port 80.
    -   The FastAPI backend is available on port 8000.
    -   The PostgreSQL database is on port 5432.

To stop the application, press `Ctrl+C` in the terminal where `docker-compose` is running, and then run:
```bash
docker-compose down
```