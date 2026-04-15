# qnn_apre.py  (run with Python 3.10+)
import pennylane as qml
from pennylane import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib

# -------------------------------
# Hyperparams
n_qubits = 6               # keep small
n_layers = 2               # variational layers
q_output_dim = n_qubits    # measure Z on each qubit
seed = 42
np.random.seed(seed)
torch.manual_seed(seed)

# -------------------------------
# Example: load your features here
# X: numpy array shape (N, k) where k <= n_qubits
# y: labels (N,)  - persona classes (0..C-1)
# For demo, generate toy random data (replace with your APRE features)
N = 300
k = n_qubits  # input features dimension
X = np.random.randn(N, k)
y = (np.sum(X, axis=1) > 0).astype(int)  # toy binary labels

# Train/test split + scaling
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=seed)
scaler = StandardScaler().fit(X_train)
X_train = scaler.transform(X_train)
X_test  = scaler.transform(X_test)

# Convert to torch tensors
X_train_t = torch.tensor(X_train, dtype=torch.float32)
X_test_t  = torch.tensor(X_test, dtype=torch.float32)
y_train_t = torch.tensor(y_train, dtype=torch.long)
y_test_t  = torch.tensor(y_test, dtype=torch.long)

# -------------------------------
# PennyLane device
dev = qml.device("default.qubit", wires=n_qubits)

# -------------------------------
# Quantum circuit: angle encoding + variational layers
def feature_map(x):
    # x is length n_qubits
    for i in range(n_qubits):
        qml.RY(x[i], wires=i)

def variational_layer(params):
    # params shape: (n_qubits, 2) maybe
    for i in range(n_qubits):
        qml.RX(params[i,0], wires=i)
        qml.RZ(params[i,1], wires=i)
    # entangling layer
    for i in range(n_qubits - 1):
        qml.CNOT(wires=[i, i+1])
    # (optionally) close ring
    qml.CNOT(wires=[n_qubits-1, 0])

# Parameterized QNode
@qml.qnode(dev, interface="torch", diff_method="parameter-shift")
def qnode(inputs, weights):
    # inputs: shape (n_qubits,), weights: shape (n_layers, n_qubits, 2)
    feature_map(inputs)
    for l in range(n_layers):
        variational_layer(weights[l])
    # measure Z expectation for each qubit -> vector of size n_qubits
    return [qml.expval(qml.PauliZ(i)) for i in range(n_qubits)]

# Wrap QNode in a torch Module
class QuantumLayer(nn.Module):
    def __init__(self, n_layers, n_qubits):
        super().__init__()
        # initialize weights small
        weight_shape = (n_layers, n_qubits, 2)
        init_weights = 0.01 * torch.randn(weight_shape, requires_grad=True)
        self.weights = nn.Parameter(init_weights)

    def forward(self, x):
        # x: (batch, k) torch tensor. We'll map per-sample via qnode
        outputs = []
        for xi in x:
            # qnode expects 1D numpy/torch; pennylane will accept torch
            evs = qnode(xi, self.weights)
            # evs may be a list of torch tensors (possibly Double) or numpy scalars.
            # Stack and convert to the same dtype and device as the input to avoid
            # mismatched-dtype errors when feeding into classical layers.
            evs_tensor = torch.stack(evs)
            if evs_tensor.dtype != x.dtype or evs_tensor.device != x.device:
                evs_tensor = evs_tensor.to(dtype=x.dtype, device=x.device)
            outputs.append(evs_tensor)
        return torch.stack(outputs)  # shape (batch, n_qubits)

# -------------------------------
# Full model: QuantumLayer -> classical head
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
        q_out = self.q_layer(x)            # (batch, n_qubits)
        logits = self.classifier(q_out)
        return logits

# -------------------------------
# Prepare, train
n_classes = 2
model = HybridModel(n_layers, n_qubits, n_classes)
opt = torch.optim.Adam(model.parameters(), lr=0.01)
loss_fn = nn.CrossEntropyLoss()

# small-batch training
epochs = 5
batch_size = 16

for epoch in range(epochs):
    model.train()
    perm = torch.randperm(X_train_t.size(0))
    loss_epoch = 0.0
    for i in range(0, X_train_t.size(0), batch_size):
        idx = perm[i:i+batch_size]
        xb = X_train_t[idx]
        yb = y_train_t[idx]
        opt.zero_grad()
        logits = model(xb)
        loss = loss_fn(logits, yb)
        loss.backward()
        opt.step()
        loss_epoch += float(loss.detach())
    # eval
    model.eval()
    with torch.no_grad():
        preds = torch.argmax(model(X_test_t), dim=1)
        acc = (preds == y_test_t).float().mean().item()
    print(f"Epoch {epoch+1}/{epochs}  loss={loss_epoch:.4f}  test_acc={acc:.3f}")

# -------------------------------
# Save trained model and scaler for later use
model_path = "qnn_model.pth"
scaler_path = "scaler.pkl"
torch.save(model.state_dict(), model_path)
joblib.dump(scaler, scaler_path)
print(f"Saved model state_dict to {model_path}")
print(f"Saved scaler to {scaler_path}")

# Example: to load the model later for inference:
# loaded_model = HybridModel(n_layers, n_qubits, n_classes)
# loaded_model.load_state_dict(torch.load(model_path))
# loaded_model.eval()
# loaded_scaler = joblib.load(scaler_path)
