# Install & Run

```bash
# Navigate to the cloned repository then,
python3 -m venv ./venv
source venv/bin/activate
pip install -r requirements.txt
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
        "torch._tensor.Tensor",
        "torch.nn.modules.rnn.RNNBase",
        "torch.nn.modules.rnn.RNN",
        "torch.nn.modules.rnn.LSTM",
        "torch.nn.modules.rnn.GRU",
        "torch.nn.modules.activation.Softmax",
        "torch.nn.modules.activation.Softmin",
        "torch.nn.modules.activation.MultiheadAttention",
        "torch.nn.modules.transformer.TransformerEncoderLayer",
        "torch.nn.modules.transformer.TransformerDecoderLayer",
        "torch.nn.functional.softmax",
        "torch.nn.functional.softmin"
    ]
}
```
