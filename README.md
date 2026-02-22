# Enhanced Smart Computing Grid Simulator

A comprehensive simulator for monitoring and optimizing computing grid performance. It features proactive load balancing, ML-based power prediction, and green savings tracking.

## Project Structure

- `main.py`: FastAPI backend simulator and API.
- `grid-frontend/`: React-based dashboard for visualizing grid status and optimization events.
- `requirements.txt`: Python dependencies for the backend.

## Key Features

- **Proactive Load Balancing**: Automatically redistributes loads to prevent overheating and optimize performance.
- **ML Power Prediction**: Uses Gradient Boosting to predict power consumption patterns and peaks.
- **Green Savings Tracking**: Calculates energy efficiency gains and CO2 impact.
- **Real-time Monitoring**: Interactive dashboard for visualizing node status, temperature, and load.

## Getting Started

### Backend Setup

1.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Backend**:
    ```bash
    uvicorn main:app --reload
    ```
    The API will be available at `http://localhost:8000`.

### Frontend Setup

1.  **Navigate to the Frontend Directory**:
    ```bash
    cd grid-frontend
    ```

2.  **Install Node Modules**:
    ```bash
    npm install
    ```

3.  **Run the Development Server**:
    ```bash
    npm run dev
    ```
    The dashboard will be available at `http://localhost:5173`.

## Technologies Used

- **Backend**: FastAPI, Uvicorn, Pydantic, NumPy, Scikit-learn, Pandas.
- **Frontend**: React, Vite, TailwindCSS, Lucide React, Recharts.
