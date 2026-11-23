"""Shared training/inference definition. No network access during inference."""
import torch
from torch import nn
from torchvision.models import resnet18
from torchvision import transforms

IMAGE_SIZE = 128
TRANSFORM = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)), transforms.ToTensor(),
    transforms.Normalize([.485, .456, .406], [.229, .224, .225]),
])

class CrackNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone = resnet18(weights=None)
        self.backbone.fc = nn.Identity()
        self.head = nn.Sequential(nn.Linear(512, 128), nn.ReLU(), nn.Dropout(.3), nn.Linear(128, 1))

    def forward(self, x):
        return self.head(self.backbone(x)).squeeze(-1)
