# CU-319 - Train a tiny network

**Objective.** Train a network of about a hundred numbers on a toy spiral in your browser, follow one forward and one backward pass by hand, prove the backward pass right with a gradient check, and find the same kind of block inside SD 1.5. Taught by Tinker Tune.

## The idea

A neural network is a stack of layers. Each layer multiplies its input by a matrix of weights, adds a bias, and bends the result with an activation such as tanh or ReLU. The last layer here gives one number, the logit, and the sigmoid of the logit is the network's probability that a point is class 1.

Training is three steps, again and again:

1. **Forward.** Run every training point through the layers and read the probabilities.
2. **Loss.** Score them with cross-entropy: small when the network is sure and right, large when it is sure and wrong.
3. **Backward.** Work out, for every weight, which way to nudge it to lower the loss, then nudge each one by the learning rate times that slope. That is gradient descent.

The backward pass is the chain rule run from the output back to the input. With a sigmoid output and cross-entropy, the slope at the logit is simply p - y: the probability minus the label.

## Try it

Two inputs, the x and y of a point. Pick the data, the number of hidden layers, the neurons per layer, the learning rate and the activation, then press Train. The background is what the network believes everywhere; the rings are points it never trains on.

{{play:mlp}}

Things to try:

- **Linear activation on the spiral.** It never gets there. The boundary stays a straight line, however many layers you add.
- **Learning rate 3.** The loss jumps about or blows up. Then 0.003: it barely moves in the time you will wait.
- **Sixteen neurons, noise 0.5.** The training dots get close to 100% while the rings fall behind. That gap is overfitting.
- **Check the gradients.** The page compares its backward pass with finite differences on the current weights.

## In ComfyUI

This is not only a toy. Every transformer block in the SD 1.5 U-Net ends with a `FeedForward` (in `comfy/ldm/modules/attention.py`): a Linear layer, then `GEGLU`, then another Linear layer, four times wider in the middle. It is the same idea as the lab's network, with a gated GELU where the lab has tanh, and 1,231,680 weights at the first width instead of 105. `BasicTransformerBlock` runs self-attention, then cross-attention with your prompt, then this FeedForward. When `KSampler` runs in the graph below, it runs thousands of these small networks for every step.

{{graph:sd15_txt2img}}

## Lab

The same maths in PyTorch, on a CPU, against autograd. First the data, the same two-arm spiral as the browser lab:

```text
spiral: 240 points, 120 of class 1, 180 to train on, 60 held out
```

**The backward pass by hand.** One hidden layer of 4 tanh neurons. Start from p - y at the output, multiply back through the weights, and through tanh's slope, 1 - tanh². The result matches autograd:

```text
hand-written backward against autograd, largest difference: 6.9e-18
```

**A gradient check.** Nudge each weight up and down by 1e-5, measure the loss each time, and compare the centred difference with the backward pass. The CS231n notes say under 1e-7 is a happy result:

```text
activation  parameters  worst relative error
tanh        51          3.8e-09
sigmoid     51          8.8e-09
```

**Training.** Full-batch gradient descent, 2500 steps, as in the browser:

```text
network        activation  rate  steps  loss before  loss after  train right  held out right
2-8-8-1        tanh        0.3   2500   0.6722       0.0545      97.8         98.3
2-8-8-1        linear      0.3   2500   0.6706       0.5152      77.2         45.0
2-8-8-1        tanh        0.003 2500   0.6722       0.5402      79.4         40.0
```

The tanh network learns the spiral. The linear one cannot, and too small a rate has hardly started. Why the linear one cannot:

```text
two linear layers against the single layer W2·W1: largest difference 1.1e-16
```

Two linear layers multiply out to one. Only the bend between them lets a network draw a curved boundary.

**Size.**

```text
SD 1.5 FeedForward at width 320: 320 -> 1280 (gated, so 2560 outputs) -> 320, 1,231,680 weights and biases
the browser lab's 2-8-8-1 network: 105 weights and biases
```

## What goes wrong

- **The loss becomes infinite.** The learning rate is too large for this network: each step overshoots further. Lower it and start from new weights.
- **The loss hardly moves.** The rate is too small, or every ReLU went dead. ReLU passes nothing below zero, and a neuron that never fires never learns. Our ReLU layers start with a small positive bias to make that rarer.
- **Training points perfect, held-out points poor.** The network learned the points rather than the shape. Fewer neurons, more data or less noise help.
- **A gradient check fails on one ReLU weight only.** A finite difference that crosses ReLU's bend at zero disagrees with the slope on one side of it. The CS231n notes call these kinks. A failure on many weights means the backward pass is wrong; the tests show the check catching a tanh derivative left out.
- **Different results from the same settings.** New starting weights give a different run. The lab fixes its seeds so its tables repeat.

## Sources

- [CS231n, Neural Networks Case Study](https://cs231n.github.io/neural-networks-case-study/)
- [CS231n, Neural Networks Part 3: gradient checks](https://cs231n.github.io/neural-networks-3/)
- [A Neural Network Playground](https://playground.tensorflow.org)
- [He, Zhang, Ren, Sun 2015. Delving Deep into Rectifiers: Surpassing Human-Level Performance on ImageNet Classification](https://arxiv.org/abs/1502.01852)
- [ComfyUI v0.43.0, comfy/ldm/modules/attention.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/ldm/modules/attention.py)
