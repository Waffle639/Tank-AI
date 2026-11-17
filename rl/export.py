"""Export a trained version to ONNX, the file the web demo runs in the browser.

Only the part that picks the buttons is exported: obs (1, 70) -> probs (1, 5), the chance of pressing each
button. An SB3 zip is ~2 MB because it also holds the value network and Adam's optimizer state, which only
matter for training; this is 85,253 numbers (~341 KB). The hidden layers' activations are extra outputs
(hidden1, hidden2, ...), so the page can show the network thinking. They add no weights.

python -m rl.export     exports every models/v*.zip whose .onnx is missing or out of date, and checks it against torch
"""
from pathlib import Path

import numpy as np

from rl.observation import OBS_SIZE


def brain(policy):
    """The policy as a torch module: obs -> (probs, hidden1, hidden2, ...), and the names of those outputs."""
    from torch import nn

    class Brain(nn.Module):
        def __init__(self):
            super().__init__()
            self.layers, self.out = policy.mlp_extractor.policy_net, policy.action_net

        def forward(self, obs):
            # The same layers model.predict runs (the features extractor only flattens), plus the Bernoulli's sigmoid
            hidden, x = [], obs
            for layer in self.layers:
                x = layer(x)
                if not isinstance(layer, nn.Linear):  # after each activation: what that layer's neurons say
                    hidden.append(x)
            return (self.out(x).sigmoid(), *hidden)

    n_hidden = sum(not isinstance(layer, nn.Linear) for layer in policy.mlp_extractor.policy_net)
    return Brain().eval(), ["probs"] + [f"hidden{k + 1}" for k in range(n_hidden)]


def export(zip_path):
    """Write <zip_path>.onnx next to the zip and return its path."""
    import logging

    import torch
    from stable_baselines3 import PPO

    logging.getLogger("torch.onnx").setLevel(logging.ERROR)  # its "torchvision is not installed" warnings
    net, outputs = brain(PPO.load(zip_path, device="cpu").policy)
    path = Path(zip_path).with_suffix(".onnx")
    # external_data=False: one self-contained file, the weights inside
    torch.onnx.export(net, (torch.zeros(1, OBS_SIZE),), path, input_names=["obs"], output_names=outputs,
                      external_data=False, verbose=False)
    return path


def probs(session, obs):
    """Chance of pressing each of the 5 buttons, from an onnx.reference.ReferenceEvaluator."""
    return session.run(["probs"], {"obs": np.asarray(obs, np.float32).reshape(1, OBS_SIZE)})[0][0]


if __name__ == "__main__":
    import onnx
    import torch
    from onnx.reference import ReferenceEvaluator
    from stable_baselines3 import PPO

    rng = np.random.default_rng(0)
    for zip_path in sorted(Path("models").glob("v*.zip")):
        path = zip_path.with_suffix(".onnx")
        policy = PPO.load(zip_path, device="cpu").policy
        net, outputs = brain(policy)
        if not path.exists() or [o.name for o in onnx.load(path).graph.output] != outputs:
            export(zip_path)
        # The ONNX file gives the same probabilities and activations as the torch policy it came from
        session = ReferenceEvaluator(onnx.load(path))
        for obs in rng.uniform(-1, 1, (20, OBS_SIZE)).astype(np.float32):
            got = session.run(None, {"obs": obs[None]})
            with torch.no_grad():
                expected = [t[0].numpy() for t in net(torch.as_tensor(obs[None]))]
                predicted = policy.get_distribution(torch.as_tensor(obs[None])).distribution.probs[0].numpy()
            assert np.allclose(got[0][0], predicted, atol=1e-5), (path, got[0][0], predicted)
            for name, g, e in zip(outputs, got, expected):
                assert np.allclose(g[0], e, atol=1e-5), (path, name)
        print(f"ok: {path} ({path.stat().st_size / 1024:.0f} KB, outputs {', '.join(outputs)})")
