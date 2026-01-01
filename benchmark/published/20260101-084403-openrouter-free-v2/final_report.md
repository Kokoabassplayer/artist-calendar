# Final Benchmark Report

## Executive Summary

This report presents a benchmark evaluation of several language models for extracting structured data from Thai tour posters. The goal is to assess their suitability for the ArtistCalendar application, focusing on the accuracy of extracted information and adherence to a predefined JSON schema. The ground truth used in this evaluation is of silver quality. The best performing model was `openrouter-google_gemma-3-12b-it_free` with an app quality score of 76.3.

## Dataset

The dataset consists of 58 Thai tour poster images sourced from Instagram, as defined by the URLs in `docs/test_poster_urls.txt`. The dataset includes single-poster images containing tour date information, while excluding multi-image carousels, non-tour announcements, and posters without dates. The dataset's identity is ensured by capturing the SHA-256 hash of the URL list and manifest.

## Methodology

The benchmark evaluates the models' ability to extract structured data from the poster images and represent it in a JSON format conforming to the schema defined in `benchmark/prompts/ground_truth.txt`. The evaluation metrics include:

*   **App Quality Score:** A composite score (0-100) that considers structured output quality, top-level field accuracy, event matching, and event count accuracy.
*   **Schema Strict Rate:** The percentage of predictions that strictly adhere to the defined JSON schema.
*   **JSON Parse Rate:** The percentage of predictions that are valid JSON.
*   **Average Scores:** Scores for top-level fields, event matching, event count, location, and venue.
*   **Average Missing Field Rate:** The average rate of missing key fields (date, venue, city, province).
*   **Average Event Difference:** The average difference between the number of events predicted and the number of events in the ground truth.
*   **Average Date F1:** The F1 score for date extraction accuracy.

Statistical reliability is assessed using bootstrap confidence intervals (1,000 resamples, seed 23, alpha 0.05). Pairwise comparisons between models are performed using bootstrap mean differences and p-values.

The temperature was fixed at 0.1 for all models, and a fixed random seed of 23 was used.

## Results

| Model                                                        | App Quality Score | Total Cost (USD) | Schema Strict Rate |
| ------------------------------------------------------------ | ----------------- | ---------------- | ------------------ |
| openrouter-google\_gemma-3-12b-it\_free                      | 76.3              | 2.308029         | 0.914              |
| openrouter-google\_gemma-3-27b-it\_free                      | 22.58             | 2.308029         | 0.241              |
| openrouter-google\_gemma-3-4b-it\_free                       | 59.08             | 2.308029         | 0.534              |
| openrouter-mistralai\_mistral-small-3.1-24b-instruct\_free | 0.0               | 2.308029         | 0.0                |
| openrouter-nvidia\_nemotron-nano-12b-v2-vl\_free            | 68.01             | 2.308029         | 0.776              |
| openrouter-qwen\_qwen-2.5-vl-7b-instruct\_free               | 70.9              | 2.308029         | 0.707              |

## Interpretation

The `openrouter-google_gemma-3-12b-it_free` model achieved the highest app quality score (76.3), indicating its superior performance in extracting accurate and structured data. The `openrouter-google_gemma-3-27b-it_free` model performed poorly, with a low app quality score (22.58) and schema strict rate (0.241), and a high number of missing predictions (39). The `openrouter-mistralai_mistral-small-3.1-24b-instruct_free` model failed to produce any valid predictions, resulting in an app quality score of 0.0.

Statistical comparisons reveal significant differences between several models. For instance, `openrouter-google_gemma-3-12b-it_free` significantly outperforms `openrouter-google_gemma-3-27b-it_free`, `openrouter-google_gemma-3-4b-it_free`, `openrouter-mistralai_mistral-small-3.1-24b-instruct_free`, and `openrouter-nvidia_nemotron-nano-12b-v2-vl_free`. The difference between `openrouter-google_gemma-3-12b-it_free` and `openrouter-qwen_qwen-2.5-vl-7b-instruct_free` was not statistically significant (p-value = 0.052).

The models all had the same total cost, as they were all free. Therefore, the primary tradeoff is between accuracy and model selection.

## Limitations

The ground truth used in this evaluation is of silver quality, meaning it was not verified by two independent human annotators and adjudicated. This limits the reliability of the benchmark results. The dataset is also limited in size and may not fully represent the diversity of Thai tour posters. The models were evaluated with a fixed temperature and seed, which may not reflect their performance under different settings. The evaluation focuses on structured output and does not consider other factors such as inference speed or resource consumption.

## Recommendations

Based on the benchmark results, the `openrouter-google_gemma-3-12b-it_free` model appears to be the most suitable for the ArtistCalendar application. However, given the silver quality of the ground truth, it is recommended to conduct further evaluation with gold-quality ground truth to confirm these findings. Further investigation is needed to understand the poor performance of the `openrouter-google_gemma-3-27b-it_free` and `openrouter-mistralai_mistral-small-3.1-24b-instruct_free` models.
