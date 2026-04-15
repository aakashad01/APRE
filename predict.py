# predict.py
# Usage examples:
#   python predict.py --sample 0.1,0.2,0.3,0.4
#   python predict.py --random
#   python predict.py --csv data.csv  # first row is taken as sample

import argparse
import joblib
import numpy as np
import torch
import torch.nn as nn
import pennylane as qml
from pennylane import numpy as pnp

# Match these to the values used when training in `qnn.py`
n_qubits = 4
n_layers = 2
n_classes = 2

# PennyLane device (same as training)
dev = qml.device("default.qubit", wires=n_qubits)

# Circuit building blocks (same as qnn.py)
def feature_map(x):
    for i in range(n_qubits):
        qml.RY(x[i], wires=i)

def variational_layer(params):
    for i in range(n_qubits):
        qml.RX(params[i,0], wires=i)
        qml.RZ(params[i,1], wires=i)
    for i in range(n_qubits - 1):
        qml.CNOT(wires=[i, i+1])
    qml.CNOT(wires=[n_qubits-1, 0])

@qml.qnode(dev, interface="torch", diff_method="parameter-shift")
def qnode(inputs, weights):
    feature_map(inputs)
    for l in range(n_layers):
        variational_layer(weights[l])
    return [qml.expval(qml.PauliZ(i)) for i in range(n_qubits)]

# Recreate QuantumLayer and HybridModel so we can load state_dict
class QuantumLayer(nn.Module):
    def __init__(self, n_layers, n_qubits):
        super().__init__()
        weight_shape = (n_layers, n_qubits, 2)
        init_weights = 0.01 * torch.randn(weight_shape, requires_grad=True)
        self.weights = nn.Parameter(init_weights)

    def forward(self, x):
        outputs = []
        for xi in x:
            evs = qnode(xi, self.weights)
            evs_tensor = torch.stack(evs)
            if evs_tensor.dtype != x.dtype or evs_tensor.device != x.device:
                evs_tensor = evs_tensor.to(dtype=x.dtype, device=x.device)
            outputs.append(evs_tensor)
        return torch.stack(outputs)

class HybridModel(nn.Module):
    def __init__(self, n_layers, n_qubits, n_classes):
        super().__init__()
        self.q_layer = QuantumLayer(n_layers, n_qubits)
        self.classifier = nn.Sequential(
            nn.Linear(n_qubits, 16),
            nn.ReLU(),
            nn.Linear(16, n_classes)
        )

    def forward(self, x):
        q_out = self.q_layer(x)
        logits = self.classifier(q_out)
        return logits


def load_model(model_path="qnn_model.pth", scaler_path="scaler.pkl"):
    scaler = joblib.load(scaler_path)
    model = HybridModel(n_layers, n_qubits, n_classes)
    state = torch.load(model_path, map_location=torch.device('cpu'))
    model.load_state_dict(state)
    model.eval()
    return model, scaler


def predict_sample(model, scaler, sample):
    # sample: 1D iterable of length n_qubits
    x = np.array(sample, dtype=float).reshape(1, -1)
    x_scaled = scaler.transform(x)
    x_t = torch.tensor(x_scaled, dtype=torch.float32)
    with torch.no_grad():
        logits = model(x_t)
        probs = torch.softmax(logits, dim=1).numpy()[0]
        pred = int(torch.argmax(logits, dim=1).item())
    return pred, probs


def parse_args():
    parser = argparse.ArgumentParser(description="Load QNN model and run inference")
    parser.add_argument("--sample", type=str, help="Comma-separated feature values (length must equal n_qubits)")
    parser.add_argument("--random", action="store_true", help="Use a random sample")
    parser.add_argument("--csv", type=str, help="CSV file; first row is used as sample")
    parser.add_argument("--model", type=str, default="qnn_model.pth", help="Path to model .pth")
    parser.add_argument("--scaler", type=str, default="scaler.pkl", help="Path to scaler .pkl")
    return parser.parse_args()


def main():
    args = parse_args()
    model, scaler = load_model(args.model, args.scaler)

    if args.sample:
        sample = [float(s) for s in args.sample.split(",")]
    elif args.csv:
        import csv
        with open(args.csv, newline='') as f:
            reader = csv.reader(f)
            first = next(reader)
            sample = [float(s) for s in first]
    elif args.random:
        sample = np.random.randn(n_qubits).tolist()
    else:
        print("No input provided. Use --sample, --csv, or --random.")
        return

    if len(sample) != n_qubits:
        print(f"Sample length {len(sample)} does not match n_qubits={n_qubits}")
        return

    pred, probs = predict_sample(model, scaler, sample)
    print("Sample:", sample)
    print("Predicted class:", pred)
    print("Class probabilities:", probs)

if __name__ == "__main__":
    main()
