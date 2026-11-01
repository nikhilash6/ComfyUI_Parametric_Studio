# CU-406 - Scaling: sharding, batching and serving

**Objective.** Work out how many jobs a ComfyUI server can take, where the time goes, and how to route jobs across several servers. Taught by Tinker Tune.

## The idea

One ComfyUI process runs one job at a time. Its queue holds the rest. To serve more people you can do three things:

- **Batch.** More images per job.
- **Queue well.** Know how full is too full.
- **Run more workers**, usually one process per GPU, and route jobs among them. Giving each worker its own share of the work is what people mean by sharding.

When jobs switch models, loading can dominate, since moving a model into memory can cost more than the job itself. In our simulation below, the routing that keeps models in place does best.

## The mechanism

**The queue.** `main.py` starts one `prompt_worker` thread, which takes one item at a time from `PromptQueue`. It's a heap ordered by a number. `POST /prompt` gives each job the next number, and `front: true` makes it negative, so it goes first. A job already running isn't pre-empted. `MAXIMUM_HISTORY_SIZE` keeps at most 10,000 finished jobs in memory.

**Batches.** `batch_size` on an empty latent makes one job produce many images. A batch shares the model load and the text encoding, and needs memory for all its images at once. You wait longer for the first image, since they all finish together. It's a throughput gain, at a latency cost.

**Busy time.** If jobs arrive every g seconds and take r seconds, the worker is busy r ÷ g of the time. Waits rise steeply well before 100%, and above 100% the queue grows without limit.

**Several workers.** ComfyUI has no built-in cluster. Run one process per GPU, with `--cuda-device` and `--port`. Something of your own then chooses a worker per job, and it must keep each job's `client_id` and `prompt_id` tied to that worker, since each server has its own queue and history.

{{play:serving}}

## In ComfyUI

Change `batch_size` on the latent node for a batch. With `LatentFromBatch`, shown below, you can re-render one image of a batch, because a batch's noise is drawn in order.

{{graph:b_batch_pick}}

Cancelling is per job: `POST /interrupt` with a `prompt_id`, or `POST /queue` with `delete`. `POST /free` unloads models, and takes effect between jobs. Reporting: `/queue`, and `/system_stats` for memory. To learn whether a worker has a model loaded you have to track it yourself, since we found no route for that among the ones we read.

## What goes wrong

- **Testing at low load, launching at high load.** At 91% busy a job in the lab takes about five times its own length from arrival to finish, about four of them spent queueing. Plan for well under 100%.
- **Evenly spreading jobs across many models.** Round robin makes each worker load models over and over. Compare the load counts below.
- **A batch runs out of memory, one image at a time doesn't.** Batches need room for all their images. Lower it, or use more jobs.
- **Using the wrong server's id.** Each process has its own queue and history. A `prompt_id` means nothing to another worker.
- **A caller gives up, and the job runs on.** Dropping an HTTP or websocket connection doesn't cancel it. Send a cancel.
- **Public access by accident.** See CU-463 before you put any of this on a network.
- **Timing the first job.** It includes the load. Measure after that, and again when models change.

## Lab

Every cost here is made up by us, and every result is a simulation. It shows shape, not your hardware. First the queue order, using the real rule:

```text
run order with front on one job: ['urgent', 'a', 'b', 'c']
```

A batch's throughput against its wait, with 2 s per job and 1 s per image:

```text
batch  seconds per job  images per second  seconds until you see anything
1      3.0              0.33               3.0
2      4.0              0.50               4.0
4      6.0              0.67               6.0
8      10.0             0.80               10.0
16     18.0             0.89               18.0
```

Going from 8 to 16 adds little throughput and nearly doubles the wait. Now routing: 3 models, a 20 s load, a 5 s job and one job every 2.5 s. Wait in this table and the last one runs from a job's arrival to its finish, so it includes the job itself.

```text
workers  routing        mean wait s  95th pct s  model loads
2        round robin    968.8        1880.6      202
2        least busy     1020.6       1878.1      199
2        sticky         589.0        1188.8      129
4        round robin    315.5        655.6       203
4        least busy     301.1        601.8       206
4        sticky         23.5         58.5        59
```

All routings at two workers are overloaded, so those waits only grow with more jobs. At four workers, sticky is the only one that keeps up. Last, busy time with no model changes:

```text
one worker, one model, 5 s per job
one job every   busy   mean wait s
20.0            25%    5.8
10.0            50%    7.5
6.0             83%    15.8
5.5             91%    25.9
4.5             111%   516.3
```

The last row keeps growing with more jobs, since the queue never empties.

## Sources

- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, server.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/server.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
