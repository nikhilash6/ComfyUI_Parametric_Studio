"""The "Train a tiny network" lab's maths (studio/web/university_mlp.js), run under node: the forward pass and loss match PyTorch on the same weights,
the backward pass matches PyTorch's autograd and central finite differences for every activation, training really learns the spiral, and a linear
network really can't. The lab is wired into the page and closes every component."""
import json, shutil, subprocess, tempfile
from pathlib import Path
import pytest

WEB = Path(__file__).resolve().parents[1] / "studio" / "web"
pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="node not installed")


def js(body):
    with tempfile.TemporaryDirectory() as t:
        d = Path(t); shutil.copy(WEB / "university_mlp.js", d / "university_mlp.js"); (d / "x.mjs").write_text('import * as M from "./university_mlp.js";\n' + body)
        p = subprocess.run(["node", str(d / "x.mjs")], capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr[-800:]
    return json.loads(p.stdout)


DUMP = '''const out = {};
for (const act of ["relu", "tanh", "sigmoid", "linear"]) {
  const net = M.init(M.sizesOf(2, 5), act, 11), d = M.dataset("spiral", 30, 0.1, 4), c = M.forward(net, d.X), g = M.backward(net, d.X, d.y, c);
  out[act] = { sizes: net.sizes, W: net.W.map((w) => Array.from(w)), b: net.b.map((v) => Array.from(v)), X: d.X, y: d.y, p: c.p, loss: M.loss(net, d.X, d.y, c), gW: g.W.map((w) => Array.from(w)), gb: g.b.map((v) => Array.from(v)), check: M.gradCheck(net, d.X, d.y) };
}
console.log(JSON.stringify(out));'''


def test_forward_loss_and_backward_match_pytorch_autograd():
    torch = pytest.importorskip("torch")
    out = js(DUMP)
    f = {"relu": torch.relu, "tanh": torch.tanh, "sigmoid": torch.sigmoid, "linear": lambda z: z}
    for act, o in out.items():
        W = [torch.tensor(w, dtype=torch.float64).view(o["sizes"][l + 1], o["sizes"][l]).requires_grad_() for l, w in enumerate(o["W"])]
        b = [torch.tensor(v, dtype=torch.float64).requires_grad_() for v in o["b"]]
        a = torch.tensor(o["X"], dtype=torch.float64)
        for l in range(len(W)):
            z = a @ W[l].T + b[l]; a = f[act](z) if l < len(W) - 1 else z
        logit = a[:, 0]; y = torch.tensor(o["y"], dtype=torch.float64)
        L = torch.nn.functional.binary_cross_entropy_with_logits(logit, y); L.backward()
        assert torch.allclose(torch.sigmoid(logit), torch.tensor(o["p"], dtype=torch.float64), atol=1e-12), act
        assert abs(L.item() - o["loss"]) < 1e-12, act
        for l in range(len(W)):
            assert torch.allclose(W[l].grad.flatten(), torch.tensor(o["gW"][l], dtype=torch.float64), atol=1e-12), (act, l)
            assert torch.allclose(b[l].grad, torch.tensor(o["gb"][l], dtype=torch.float64), atol=1e-12), (act, l)


def test_gradient_check_agrees_with_backward_for_every_activation():
    out = js(DUMP)
    for act, o in out.items():
        assert o["check"]["checked"] == sum(len(w) for w in o["W"]) + sum(len(v) for v in o["b"]) and o["check"]["worst"] < 1e-5, (act, o["check"])


def test_the_check_catches_a_wrong_backward_pass():
    o = js('''const net = M.init(M.sizesOf(1, 4), "tanh", 2), d = M.dataset("xor", 16, 0.1, 3);
const real = M.ACTS.tanh.d; M.ACTS.tanh.d = (z) => 1;            // the derivative of tanh "forgotten"
const bad = M.gradCheck(net, d.X, d.y); M.ACTS.tanh.d = real; const good = M.gradCheck(net, d.X, d.y);
console.log(JSON.stringify({ bad: bad.worst, good: good.worst }));''')
    assert o["bad"] > 1e-3 and o["good"] < 1e-6


def test_training_learns_the_spiral_and_a_linear_network_cannot():
    o = js('''const run = (act, L, W, lr, n) => { const d = M.split(M.dataset("spiral", 240, 0.1, 7)), net = M.init(M.sizesOf(L, W), act, 1); const first = M.loss(net, d.train.X, d.train.y); let r;
  for (let i = 0; i < n; i++) r = M.step(net, d.train.X, d.train.y, lr);
  return { first, last: M.loss(net, d.train.X, d.train.y), train: M.accuracy(net, d.train.X, d.train.y), test: M.accuracy(net, d.test.X, d.test.y), moved: r.moved }; };
console.log(JSON.stringify({ tanh: run("tanh", 2, 8, 0.3, 2500), linear: run("linear", 2, 8, 0.3, 2500), huge: run("tanh", 2, 8, 3000, 50) }));''')
    t = o["tanh"]; assert t["train"] >= 0.95 and t["test"] >= 0.9 and t["last"] < t["first"] / 10 and t["moved"] > 0
    assert o["linear"]["train"] < 0.85 and o["linear"]["test"] < 0.85                     # straight-line maps stacked are still one straight line
    assert o["huge"]["last"] > o["tanh"]["last"]                                        # far too big a step does not learn


def test_data_is_seeded_balanced_and_split():
    o = js('''const a = M.dataset("circles", 40, 0.1, 5), b = M.dataset("circles", 40, 0.1, 5), c = M.dataset("circles", 40, 0.1, 6), s = M.split(M.dataset("spiral", 40));
const all = M.DATASETS.map(([k]) => { const d = M.dataset(k, 200, 0.1, 1); return [k, d.y.reduce((t, v) => t + v, 0), Math.max(...d.X.flat().map(Math.abs))]; });
console.log(JSON.stringify({ same: JSON.stringify(a) === JSON.stringify(b), differs: JSON.stringify(a) !== JSON.stringify(c), split: [s.train.y.length, s.test.y.length], all, params: M.paramCount(M.init(M.sizesOf(2, 8), "relu", 1)), field: M.field(M.init(M.sizesOf(1, 3), "tanh", 1), 6).length }));''')
    assert o["same"] and o["differs"] and o["split"] == [30, 10] and o["params"] == 2 * 8 + 8 + 8 * 8 + 8 + 8 + 1 and o["field"] == 36
    for k, ones, big in o["all"]: assert 70 <= ones <= 130 and big < 1.6, k


def test_the_lab_is_on_the_page():
    plays = (WEB / "university_plays.js").read_text(); nn = (WEB / "university_plays_nn.js").read_text()
    assert 'import { MORE as NN } from "./university_plays_nn.js"' in plays and "Object.assign(PLAYS, NN)" in plays and "\n  mlp: { title:" in nn
    assert "http" not in nn and "http" not in (WEB / "university_mlp.js").read_text()          # no fetch at runtime, no CDN
