# Inventory Policy Workflow — Problem Statement

## The Problem

At large retailers, category business owners translate quarterly budget and service-level targets (e.g., "$100M budget, 97% in-stock") into inventory policies — safety stock, item-level service levels (DCC), reorder points, order frequency, MOQ thresholds — across item segments. These policies then feed directly into replenishment engines that auto-purchase for 3-4 months.

Today, the step where these policies get *defined* runs entirely in Excel. Internal data science teams have built simulations that show what a given set of configs *will do* downstream — but no tool answers the upstream question: **given my budget and goals, what should the configs *be*?** Each "what if" at the budget↔policy level takes hours. Teams explore 2-3 scenarios when 20+ should be evaluated, then commit to policies they can't fully validate — policies that will control automated spending for an entire season.

## Why It Matters

On a $100M budget, even a 3-5% improvement in allocation efficiency — well within published industry benchmarks — represents **$3-5M in avoidable margin loss per department per cycle**, primarily from markdowns on overstock and lost sales from stockouts driven by suboptimal allocation. These errors compound because policies are sticky — DCC configs rarely change mid-season, safety stock is usually unchanged — so wrong settings auto-execute for months.

## What I'm Building

An AI-powered policy optimization surface that sits upstream of existing simulation and replenishment systems. It takes budget + service-level goals as input and outputs the optimal set of inventory configs across all item segments — then lets the CBO explore alternatives instantly ("What if budget drops $3M? What if we push DCC to 98% on A-items only?"). Two-tier execution model: auto-configure routine parameters, surface high-stakes decisions with quantified trade-offs for human approval.

Not a simulation. Not a replenishment engine. The step that comes *before* both — figuring out what the configs should be, so there's something worth simulating and something right to automate.
