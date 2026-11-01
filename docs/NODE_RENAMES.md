# Node ids changed by the audit of 2026-11-01

These nodes implied work they did not do, so they were renamed to say what they are, and any fabricated output was dropped. A graph that used an old id reports it as a missing node: swap in the new one and check the outputs you wired, since some are gone. Those outputs were never real.

| Old id | New id |
|---|---|
| `PSN_ACES_OutputTransform` | `PSN_ACES_OutputConfig_Check` |
| `PSN_Agent_Executor` | `PSN_Agent_Transform_Sim` |
| `PSN_Anime_Segmentor` | `PSN_BandColorThresholdMask` |
| `PSN_Archive_Logger` | `PSN_Archive_Line_Format` |
| `PSN_AudioNotifier` | `PSN_Audio_Notify_Payload` |
| `PSN_AutoRescaleCFG` | `PSN_CFG_Rescale_Calculator` |
| `PSN_BM3D_Denoise` | `PSN_PatchDCT_Shrink` |
| `PSN_BaselineSampler` | `PSN_KSampler_Graph_Builder` |
| `PSN_BatchExecutor` | `PSN_PromptPlaceholderImages` |
| `PSN_C2PA_Signer` | `PSN_Manifest_HMAC_Embed` |
| `PSN_C2PA_Verifier` | `PSN_Manifest_HMAC_Check` |
| `PSN_CV_RunTracker` | `PSN_Log_Entry_Formatter` |
| `PSN_Cloud_LLM_Fallback` | `PSN_LLM_Route_Decision` |
| `PSN_Conditioning_Clamp` | `PSN_Number_List_Clamp` |
| `PSN_Conditioning_Variation_Generator` | `PSN_Prompt_Weight_Variation_Specs` |
| `PSN_ContinuityEnforcer` | `PSN_ContinuityColourCheck` |
| `PSN_Crew_Prompt_Generator` | `PSN_Role_Text_Concat` |
| `PSN_DeclarativeAgentPipeline` | `PSN_AgentSchemaCheck` |
| `PSN_Distribute_Model` | `PSN_Device_Layer_Plan` |
| `PSN_Document_Quality_Assessor` | `PSN_Document_Quality_Score_From_Metrics` |
| `PSN_ELLA_Semantic_Connector` | `PSN_ELLA_Request_Formatter` |
| `PSN_FBXLoad_Render` | `PSN_Cube_Preview_Render` |
| `PSN_FaceQualityScorer` | `PSN_Image_Sharpness_Noise_Score` |
| `PSN_FilmEmulation` | `PSN_FilmGrainLUT` |
| `PSN_GazeEstimator` | `PSN_GazeVectorNormalize` |
| `PSN_Gemini_Prompt_Crafter` | `PSN_Gemini_Response_Parser` |
| `PSN_GlobalSeedBroadcaster` | `PSN_Seed_Source` |
| `PSN_GuidanceDecomposer` | `PSN_Vector2D_Decompose` |
| `PSN_HDR_Color_Manager` | `PSN_HDR_Color_Config` |
| `PSN_HDR_EXR_Save` | `PSN_EXR_Save_Plan` |
| `PSN_Inspect_Model` | `PSN_Inspect_JSON_Weights` |
| `PSN_LLM_Agent_Chat` | `PSN_LLM_Chat_Request_Build` |
| `PSN_LLM_Doc_Generator` | `PSN_Text_Blocks_To_Markdown` |
| `PSN_LoRA_Train_HunYuan` | `PSN_LoRA_Job_Payload_HunYuan` |
| `PSN_LocalLLMPromptEnhancer` | `PSN_PromptStyleTemplate` |
| `PSN_MatrixGame_Load` | `PSN_MatrixGame_ParamCheck` |
| `PSN_Merge_Checkpoints` | `PSN_Merge_JSON_Weights` |
| `PSN_MetadataInjector` | `PSN_Metadata_Tag_Carrier` |
| `PSN_Modal_Submit_Workflow` | `PSN_Modal_Job_Spec` |
| `PSN_Model_Vram_Optimizer` | `PSN_VramBudgetPlanner` |
| `PSN_MongoDB_Load_Prompt` | `PSN_Prompt_Document_Lookup` |
| `PSN_MongoDB_Save_Prompt` | `PSN_Prompt_Document_Build` |
| `PSN_Motion_Position_Effector` | `PSN_Motion_Position_Curve` |
| `PSN_MouthComposite` | `PSN_Mask_Weight_Check` |
| `PSN_MultiView_Generator` | `PSN_MultiView_Shift_Preview` |
| `PSN_Music_Generate` | `PSN_Music_Plan` |
| `PSN_NAFNet_Denoise` | `PSN_NAFNet_Config_Check` |
| `PSN_News_Video_Aggregator` | `PSN_News_Thumbnail_Placeholder` |
| `PSN_Notif_Play` | `PSN_Notif_Select` |
| `PSN_PBR_Delight` | `PSN_PBR_From_Albedo` |
| `PSN_PDF_Structured_Extractor` | `PSN_Text_Block_Splitter` |
| `PSN_Parallax_Video_Assembler` | `PSN_Parallax_Filename_Builder` |
| `PSN_PresetSaver` | `PSN_Preset_Json_Build` |
| `PSN_PromptEnhancer` | `PSN_Prompt_Reply_Parser` |
| `PSN_Prompt_Refiner_Loop` | `PSN_Prompt_Scripted_Rewrite` |
| `PSN_QuantizationMonitor` | `PSN_Quantization_Savings_Calc` |
| `PSN_RegionalPrompt` | `PSN_RegionalPrompt_Plan` |
| `PSN_SAM_Segmenter` | `PSN_PointBoxMask` |
| `PSN_ScheduledCFG` | `PSN_CFG_Schedule_Interpolator` |
| `PSN_Semantic_Index_Builder` | `PSN_Keyword_Index_Builder` |
| `PSN_Semantic_Mask_Gen` | `PSN_LuminanceSaturationMask` |
| `PSN_Semantic_Search_Query` | `PSN_Keyword_Search_Query` |
| `PSN_Sep_Split` | `PSN_Sep_Plan` |
| `PSN_Sig_Process` | `PSN_Audio_Json_Smooth_Gain_Normalize` |
| `PSN_Smart_Tile_Prompter` | `PSN_TileGrid` |
| `PSN_SmokeTestWorkflow` | `PSN_TensorExpectationCheck` |
| `PSN_StatusPollInstance` | `PSN_StatusScoreSnapshot` |
| `PSN_Stream_Step` | `PSN_Stream_Schedule_Step` |
| `PSN_StyleGAN_Generate` | `PSN_StyleGAN_Generate_Spec` |
| `PSN_StyleGAN_Load` | `PSN_StyleGAN_Path_Check` |
| `PSN_SubgraphWrapper` | `PSN_Dict_Router` |
| `PSN_TD_FrameEncode` | `PSN_TD_FrameEncode_Size` |
| `PSN_Telegram_Listener` | `PSN_Telegram_Update_Parser` |
| `PSN_Tensor_Save` | `PSN_Tensor_Save_Plan` |
| `PSN_TextToMotion_Generate` | `PSN_Random_Motion_Test_Fixture` |
| `PSN_Tiled_Renderer` | `PSN_Tile_Plan_Stitch` |
| `PSN_Tripo_Image_To_3D` | `PSN_Tripo_Image_Request_Builder` |
| `PSN_Tripo_Text_To_3D` | `PSN_Tripo_Text_Request_Builder` |
| `PSN_Tutorial_OCR_Extractor` | `PSN_TextLinesToRegions` |
| `PSN_UpscaleOnGPU` | `PSN_NearestUpscaleBatch` |
| `PSN_VLM_Caption_Generator` | `PSN_Image_Stats_Caption` |
| `PSN_VRAMGuard` | `PSN_VRAM_Bytes_Check` |
| `PSN_VRAM_Guard` | `PSN_VRAM_Budget_Compare` |
| `PSN_VRAM_History_Logger` | `PSN_VRAM_Samples_Formatter` |
| `PSN_VRAM_Query` | `PSN_VRAM_Utilization_Calc` |
| `PSN_VideoQualityMetric` | `PSN_VideoFrameDiffMetric` |
| `PSN_Video_Assembler` | `PSN_Latent_RGB_Stack` |
| `PSN_Video_Frame_Captioner` | `PSN_Frame_Description_Aggregator` |
| `PSN_Video_Frame_Generator` | `PSN_Synthetic_Latent_Frame` |
| `PSN_Video_Frame_Loop` | `PSN_Synthetic_Latent_Loop` |
| `PSN_VitMatteAlpha` | `PSN_TrimapMaskFeather` |
| `PSN_VramRelease` | `PSN_VramLedgerRelease` |
| `PSN_VramReserve` | `PSN_VramLedgerReserve` |
| `PSN_WirelessRouter` | `PSN_Route_Record` |
| `PSN_WorkflowStructure` | `PSN_WorkflowBundle` |
| `PSN_Workflow_Plugin_Exposer` | `PSN_Workflow_Plugin_Descriptor` |
| `PSN_ZImage_Grid_Generator` | `PSN_ZImage_Grid_Spec` |
| `PSN_ZImage_Grid_Visualizer` | `PSN_ZImage_Grid_Layout` |
| `PSN_ZeroCLIPConditioner` | `PSN_SeedHashVector` |

## Removed

No real behaviour existed to keep. Core ComfyUI nodes or the `PSN_Latent*` nodes cover the ones that had a real purpose.

- `PSN_Actual_Denoise`
- `PSN_Alpha_VAE_Decode`
- `PSN_Alpha_VAE_Encode`
- `PSN_Anime_Pose_Estimator`
- `PSN_Artifact_Retriever`
- `PSN_AudioSampler`
- `PSN_AutoGen_Debugger`
- `PSN_Block_Offload_Manager`
- `PSN_CachedIdentityGenerator`
- `PSN_CharacterFeatureCache`
- `PSN_Classic_Game_UI`
- `PSN_Denoise_Preview`
- `PSN_Gather_Results`
- `PSN_Generate_Speech`
- `PSN_LTX2_Identity_Lock`
- `PSN_LTX2_Stabilize`
- `PSN_Latent_Batch_Merge`
- `PSN_Latent_Batch_Repeat`
- `PSN_Latent_Batch_Split`
- `PSN_Load_Voice_Reference`
- `PSN_MatrixGame_Generate`
- `PSN_ModelMix`
- `PSN_NodeProfiler`
- `PSN_Node_Gate`
- `PSN_Peek_Sampler`
- `PSN_S3_Asset_Loader`
- `PSN_SidecarGuardedTask`
- `PSN_SmartLoRALoader`
- `PSN_SpectralSampler`
- `PSN_Step_Skip_Accelerator`
- `PSN_Video_Dubbing`
- `PSN_VramGate`
- `PSN_Weight_Ferry`
- `PSN_Workflow_Structure`
