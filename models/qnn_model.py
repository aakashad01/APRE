import torch
import torch.nn as nn
import pennylane as qml

class HybridQNN(nn.Module):
    def __init__(self, n_features, n_classes, n_qubits=4, n_layers=2):
        super(HybridQNN, self).__init__()
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        
        # 1. Classical Compression Layer
        # Compresses high-dimensional features (e.g. 20) down to n_qubits (e.g. 4)
        self.cl_layer1 = nn.Linear(n_features, n_qubits)
        self.activation = nn.Tanh() # Tanh scales to [-1, 1], good for rotation angles
        
        # 2. Quantum Layer Definition
        self.dev = qml.device("default.qubit", wires=n_qubits)
        
        @qml.qnode(self.dev, interface="torch")
        def quantum_circuit(inputs, weights):
            # Angle Embedding (Encode latent features as qubit rotations)
            # Normalize inputs to [0, PI] for optimal embedding? Tanh gives [-1,1].
            # Multiplying by PI gives [-PI, PI].
            qml.templates.AngleEmbedding(inputs * torch.pi, wires=range(n_qubits))
            
            # Variational Layers (The "Quantum Brain")
            qml.templates.StronglyEntanglingLayers(weights, wires=range(n_qubits))
            
            # Measurement
            return [qml.expval(qml.PauliZ(w)) for w in range(n_qubits)]
            
        # Create a Torch layer from the QNode
        weight_shapes = {"weights": (n_layers, n_qubits, 3)}
        self.q_layer = qml.qnn.TorchLayer(quantum_circuit, weight_shapes)
        
        # 3. Classical Output Layer
        # Maps quantum expectations (4 values) to class probabilities (5 personas)
        self.cl_layer2 = nn.Linear(n_qubits, n_classes)
        self.softmax = nn.Softmax(dim=1)
        
    def forward(self, x):
        # x shape: [batch_size, n_features]
        
        # Classical Compression
        x = self.cl_layer1(x)
        x = self.activation(x)
        
        # Quantum Processing
        x = self.q_layer(x)
        
        # Classical Classification
        x = self.cl_layer2(x)
        # Note: Usually we return raw logits for CrossEntropyLoss, handle softmax outside or inside loss.
        # But if user wants probabilities for Deception Engine, we can return both or just logits.
        # For training stability, return logits.
        return x

if __name__ == "__main__":
    # Test the model
    n_feat = 10
    n_class = 5
    model = HybridQNN(n_feat, n_class)
    sample = torch.rand(2, n_feat)
    output = model(sample)
    print("Model Output Shape:", output.shape)
    print("Model Output:", output)
