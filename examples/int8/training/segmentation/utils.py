import torch
import torchvision
from dataset import SceneParsingDataset

from torch.utils.data import DataLoader

THRESHOLD = 0.5
EPSILON = 1e-7

def get_loaders(
    train_dir,
    train_mask_dir,
    val_dir,
    val_mask_dir,
    batch_size,
    train_transform,
    val_transform,
    num_workers=2,
    pin_memory=True
):
    train_ds = SceneParsingDataset(
        image_dir = train_dir,
        mask_dir = train_mask_dir,
        transform = train_transform,
    )

    train_loader = DataLoader(
        train_ds,
        batch_size = batch_size,
        num_workers = num_workers,
        pin_memory = pin_memory,
        shuffle = True
    )

    val_ds = SceneParsingDataset(
        image_dir = val_dir,
        mask_dir = val_mask_dir,
        transform = val_transform,
        training=False,
    )

    val_loader = DataLoader(
        val_ds,
        batch_size = batch_size,
        num_workers = num_workers,
        pin_memory = pin_memory,
        shuffle = False
    )

    return train_loader, val_loader

def save_checkpoint(state, CHECKPOINT_NAME):
    print("Saving checkpoint")
    torch.save(state, CHECKPOINT_NAME)

def load_checkpoint(checkpoint, model):
    print("Loading model")
    model.load_state_dict(checkpoint["state_dict"])

def compute_dice_score(pred, label):
    pred = (pred > THRESHOLD).float()
    intersection = torch.sum(pred * label)
    union = torch.sum(pred) + torch.sum(label)
    score = (2. * intersection) / (union + EPSILON)
    return score

def check_accuracy(loader, model, device="cuda"):
    eval_loss = 0.0
    loss_fn = CustomLoss()
    dice_score = 0.0

    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            y = y.long().to(device).unsqueeze(dim=1)

            pred = model(x)
            loss = loss_fn(pred, y.float())
            eval_loss += loss.item() * x.size(0)

            dice_coef = compute_dice_score(pred.cpu(), y.cpu()).item()
            dice_score += dice_coef * x.size(0)

    print(f"Validation Loss: {eval_loss/len(loader.dataset):.4f}")
    print(f"Dice score: {dice_score/len(loader.dataset):.4f}")

class CustomLoss(torch.nn.Module):
    def __init__(self):
        super(CustomLoss, self).__init__()
        self.bce = torch.nn.BCEWithLogitsLoss(reduction='mean')
    
    def forward(self, pred, label):
        dice_score = compute_dice_score(pred, label)
        bce_score = self.bce(pred, label)
        return dice_score + bce_score
