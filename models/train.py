import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score
import os
from .qnn_model import HybridQNN

DATA_FILE = "data/processed/features.csv"
MODEL_PATH = "checkpoints/qnn_model.pth"
os.makedirs("checkpoints", exist_ok=True)

def train_model():
    print("[*] Loading Dataset...")
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found. Run extract_features.py first.")
        return

    df = pd.read_csv(DATA_FILE)
    
    # Preprocessing
    X = df.drop(columns=['label', 'client_ip'])
    y = df['label']
    
    # Encode Labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    print(f"Classes: {le.classes_}")
    
    # Scale Features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_encoded, test_size=0.2, random_state=42)
    
    # Convert to Tensor
    X_train_t = torch.tensor(X_train, dtype=torch.float32)
    y_train_t = torch.tensor(y_train, dtype=torch.long)
    X_test_t = torch.tensor(X_test, dtype=torch.float32)
    # y_test_t = torch.tensor(y_test, dtype=torch.long)
    
    # Initialize Model
    n_features = X_train.shape[1]
    n_classes = len(np.unique(y_encoded))
    
    model = HybridQNN(n_features, n_classes)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.01)
    
    print("[*] Starting Training...")
    epochs = 20 # Keep it short for demo
    
    for epoch in range(epochs):
        optimizer.zero_grad()
        outputs = model(X_train_t)
        loss = criterion(outputs, y_train_t)
        loss.backward()
        optimizer.step()
        
        if (epoch+1) % 5 == 0:
            print(f"Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}")
            
    # Evaluation
    model.eval()
    with torch.no_grad():
        test_outputs = model(X_test_t)
        _, predicted = torch.max(test_outputs.data, 1)
        acc = accuracy_score(y_test, predicted.numpy())
        print(f"[*] Test Accuracy: {acc*100:.2f}%")
        
    # Save
    torch.save({
        'model_state_dict': model.state_dict(),
        'encoder_classes': le.classes_,
        'scaler_mean': scaler.mean_,
        'scaler_scale': scaler.scale_
    }, MODEL_PATH)
    print(f"[*] Model saved to {MODEL_PATH}")

if __name__ == "__main__":
    train_model()
