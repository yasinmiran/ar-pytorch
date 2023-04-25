# Install & Run

```bash
pip3 install -r requirements.txt
uvicorn main:app --reload
```


```

Navigate to localhost:8000/

Submit an example JSON:
{
    "root_namespaces": [
        "torch.utils.checkpoint.CheckpointFunction",
        "torch.autograd.function._SingleLevelFunction",
        "torch.autograd.function.Function",
        "torch.nn.modules.activation.ReLU",
        "torch.nn.modules.activation.Threshold",
        "torch.nn.modules.conv._ConvNd",
        "torch.nn.modules.conv.Conv1d",
        "torch.nn.modules.conv.Conv2d",
        "torch.nn.modules.conv.Conv3d",
        "torch.nn.functional.relu",
        "torch.nn.functional.threshold",
        "torch._tensor.Tensor"
    ]
}
```
