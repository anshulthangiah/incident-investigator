/* Recorded output of the real command line (scripted stand-in) on the mock system, plus one real-model report read from evals/published/. Written by scripts/record_demo.py; do not edit by hand. */
window.RECORDINGS = {
 "recordings": [
  {
   "id": "S7",
   "title": "No fault",
   "question": "A few people complained about verification codes. Is anything wrong?",
   "expected_outcome": "no_issue",
   "banner": "[SCRIPTED STAND-IN, NOT AI] The text below comes from fixed keyword rules and a template, not from a language model. It only repeats numbers from the tool results and can miss or misread anything.",
   "tools_unavailable": "not available this run: check_numbers (the PM gave no phone numbers (use --number, --numbers-file or --prompt-numbers)), check_code_api (the API check is switched off (PROBE_ENABLED is not true; the PM can turn it on and approve each run))",
   "calls": [
    {
     "id": "E1",
     "tool": "fetch_delivery_logs",
     "args": {
      "start_date": "2026-11-10",
      "end_date": "2026-11-16"
     },
     "result": {
      "source": "provider_live_api",
      "days": [
       "2026-11-10",
       "2026-11-11",
       "2026-11-12",
       "2026-11-13",
       "2026-11-14",
       "2026-11-15",
       "2026-11-16"
      ],
      "total": 4540,
      "delivered": 4447,
      "failed": 93,
      "failure_rate_pct": 2.0,
      "requests_per_day": {
       "2026-11-10": 812,
       "2026-11-11": 741,
       "2026-11-12": 773,
       "2026-11-13": 831,
       "2026-11-14": 601,
       "2026-11-15": 511,
       "2026-11-16": 271
      },
      "failure_rate_pct_per_day": {
       "2026-11-10": 2.5,
       "2026-11-11": 1.2,
       "2026-11-12": 2.2,
       "2026-11-13": 1.9,
       "2026-11-14": 2.7,
       "2026-11-15": 2.0,
       "2026-11-16": 1.8
      },
      "days_without_data": [],
      "failure_reasons": [
       {
        "reason": "Recipient unreachable",
        "meaning": "The provider could not reach the recipient's phone (switched off, no coverage or full inbox).",
        "category": "Recipient device",
        "who_fixes": "Usually nothing to fix on the sending side; the phone is off, full or out of coverage.",
        "count": 59
       },
       {
        "reason": "Recipient opted out",
        "meaning": "The recipient has chosen not to receive messages of this kind.",
        "category": "Opt-out preference",
        "who_fixes": "The recipient's own preference; if it hits verification codes, check the message category registered with the provider.",
        "count": 28
       },
       {
        "reason": "Message expired",
        "meaning": "The message waited too long for delivery and the provider dropped it.",
        "category": "Network",
        "who_fixes": "Usually nothing to fix on the sending side; a temporary operator or network problem. Persistent cases go to the provider.",
        "count": 6
       }
      ],
      "failures_by_category": {
       "Recipient device": 59,
       "Opt-out preference": 28,
       "Network": 6
      },
      "templates": [
       [
        "tpl-0001",
        2791
       ],
       [
        "tpl-0002",
        1096
       ],
       [
        "tpl-0003",
        653
       ]
      ],
      "distinct_recipients": 501,
      "recipient_digit_lengths": {
       "12": 4540
      },
      "notes": [],
      "failures_by_group": {
       "route": {
        "whole_window": [
         {
          "value": "5",
          "requests": 1168,
          "failed": 27,
          "failure_rate_pct": 2.3
         },
         {
          "value": "4",
          "requests": 3372,
          "failed": 66,
          "failure_rate_pct": 2.0
         }
        ],
        "latest_day": [
         {
          "value": "4",
          "requests": 198,
          "failed": 4,
          "failure_rate_pct": 2.0
         },
         {
          "value": "5",
          "requests": 73,
          "failed": 1,
          "failure_rate_pct": 1.4
         }
        ]
       },
       "sender": {
        "whole_window": [
         {
          "value": "MOCKA",
          "requests": 3201,
          "failed": 68,
          "failure_rate_pct": 2.1
         },
         {
          "value": "MOCKB",
          "requests": 1339,
          "failed": 25,
          "failure_rate_pct": 1.9
         }
        ],
        "latest_day": [
         {
          "value": "MOCKA",
          "requests": 194,
          "failed": 5,
          "failure_rate_pct": 2.6
         },
         {
          "value": "MOCKB",
          "requests": 77,
          "failed": 0,
          "failure_rate_pct": 0.0
         }
        ]
       },
       "template": {
        "whole_window": [
         {
          "value": "tpl-0002",
          "requests": 1096,
          "failed": 29,
          "failure_rate_pct": 2.6
         },
         {
          "value": "tpl-0003",
          "requests": 653,
          "failed": 13,
          "failure_rate_pct": 2.0
         },
         {
          "value": "tpl-0001",
          "requests": 2791,
          "failed": 51,
          "failure_rate_pct": 1.8
         }
        ],
        "latest_day": [
         {
          "value": "tpl-0002",
          "requests": 54,
          "failed": 2,
          "failure_rate_pct": 3.7
         },
         {
          "value": "tpl-0003",
          "requests": 45,
          "failed": 1,
          "failure_rate_pct": 2.2
         },
         {
          "value": "tpl-0001",
          "requests": 172,
          "failed": 2,
          "failure_rate_pct": 1.2
         }
        ]
       }
      },
      "latest_day_utc": "2026-11-16",
      "failures_by_hour_latest_day": [
       {
        "hour": 0,
        "requests": 5,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 1,
        "requests": 7,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 2,
        "requests": 4,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 3,
        "requests": 4,
        "failed": 1,
        "failure_rate_pct": 25.0
       },
       {
        "hour": 4,
        "requests": 4,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 5,
        "requests": 6,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 6,
        "requests": 26,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 7,
        "requests": 40,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 8,
        "requests": 38,
        "failed": 2,
        "failure_rate_pct": 5.3
       },
       {
        "hour": 9,
        "requests": 48,
        "failed": 1,
        "failure_rate_pct": 2.1
       },
       {
        "hour": 10,
        "requests": 47,
        "failed": 1,
        "failure_rate_pct": 2.1
       },
       {
        "hour": 11,
        "requests": 42,
        "failed": 0,
        "failure_rate_pct": 0.0
       }
      ],
      "concentration": null,
      "repeat_requests": {
       "window_minutes": 10,
       "recipients_with_a_repeat": 52,
       "repeat_requests": 55,
       "recipients_with_two_or_more_repeats": 3,
       "share_of_requests_pct": 1.2,
       "share_of_requests_pct_per_day": {
        "2026-11-10": 1.8,
        "2026-11-11": 1.6,
        "2026-11-12": 0.8,
        "2026-11-13": 1.3,
        "2026-11-14": 1.0,
        "2026-11-15": 0.8,
        "2026-11-16": 0.4
       },
       "note": "A repeat is a request for the same number within the code validity window of the one before. A newer code replaces the older one, so repeats are one reason a code typed by the user can be 'invalid'. The logs cannot show which code the user typed."
      },
      "delivery_delay_s": {
       "median": 6.0,
       "p90": 9.0,
       "max": 9.0
      },
      "api_failed_calls": {
       "total": 2,
       "by_error_code": [
        {
         "error_code": "E110",
         "count": 2,
         "label": "Duplicate within 20 seconds",
         "meaning": "The same request was received twice within 20 seconds and the second was dropped. Normal on its own."
        }
       ],
       "per_day": {
        "2026-11-15": {
         "E110": 2
        }
       },
       "note": "These calls were refused before submission, so they have no row in the delivery logs. E110 (duplicate within 20 seconds) is normal at a low level."
      }
     },
     "shortened_for_display": false
    }
   ],
   "report": "[SCRIPTED STAND-IN, NOT AI] The text below comes from fixed keyword rules and a template, not from a language model. It only repeats numbers from the tool results and can miss or misread anything.\n\n1) Verdict\nNo clear fault found by the fixed rules. Confidence: low. This is not proof that nothing is wrong. [E1]\n\n2) Evidence\n- Volume: 4540 requests over 7 days, 93 failed (2 percent) [E1]\n- Requests per day [E1]\n  - 10 Nov: 812 requests, 2.5 percent failed\n  - 11 Nov: 741 requests, 1.2 percent failed\n  - 12 Nov: 773 requests, 2.2 percent failed\n  - 13 Nov: 831 requests, 1.9 percent failed\n  - 14 Nov: 601 requests, 2.7 percent failed\n  - 15 Nov: 511 requests, 2 percent failed\n  - 16 Nov: 271 requests, 1.8 percent failed\n- Most common failure reason: Recipient unreachable (59 rows). Category: Recipient device. Who fixes it: Usually nothing to fix on the sending side; the phone is off, full or out of coverage. [E1]\n- Delivery delay at the provider: median 6.0 s, p90 9.0 s, max 9.0 s [E1]\n\n3) Not checked / limits\n- Checks that ran: fetch_delivery_logs. This scripted stand-in does not decide which causes are ruled out, so treat every other cause as not yet checked [E1].\n- Not visible to any tool here: the API server's own log, the database scheduler, the code that validates a code, and anything outside the configured sources.\n- check_numbers was not run: the PM gave no phone numbers.\n- check_code_api was not run: the API check is switched off.\n\n4) Suggested next steps\n- Add a more specific symptom or the affected dates and run again.\n\n5) Information needed from you\n1. The dates and times when people saw the problem, and which app or screen they used\n   - Why: the rules read a whole window and can miss a short or narrow fault\n   - How or who to ask: ask the people who reported it, then run again with those dates in the question\n2. One or two phone numbers of affected users\n   - Why: the tool can then look at those users' requests and repeats (it sees aliases such as N1, never the numbers)\n   - How or who to ask: use --number or --prompt-numbers\n3. The verification API server's own log for a time when it failed\n   - Why: some faults leave nothing in the delivery log and no tool here can read that log\n   - How or who to ask: ask engineering\n\nOptional checks that are switched off in this run: the test-message check of the verification API (set PROBE_ENABLED and use --approve-probe; it sends one real message to your own test number).",
   "eval": {
    "expected_outcome": "no_issue",
    "outcome_from_report": "no_issue",
    "checks_passed": 6,
    "checks_total": 7,
    "failed_checks": [
     "shortest_path"
    ],
    "scored_by": "evals/run_evals.py score() applied to this recorded report"
   },
   "cost_line": "This round: no language model was used (scripted stand-in), cost 0.",
   "source": "python3 investigate.py --demo --mock-scenario S7 \"<question>\"",
   "source_kind": "scripted_stand_in"
  },
  {
   "id": "S21",
   "title": "Login says the code is invalid because repeated requests replaced earlier codes",
   "question": "Users say the login screen tells them the code is invalid even though they typed the code they received. Are the messages failing?",
   "expected_outcome": "cause_found",
   "banner": "[SCRIPTED STAND-IN, NOT AI] The text below comes from fixed keyword rules and a template, not from a language model. It only repeats numbers from the tool results and can miss or misread anything.",
   "tools_unavailable": "not available this run: check_numbers (the PM gave no phone numbers (use --number, --numbers-file or --prompt-numbers)), check_code_api (the API check is switched off (PROBE_ENABLED is not true; the PM can turn it on and approve each run))",
   "calls": [
    {
     "id": "E1",
     "tool": "fetch_delivery_logs",
     "args": {
      "start_date": "2026-11-10",
      "end_date": "2026-11-16"
     },
     "result": {
      "source": "provider_live_api",
      "days": [
       "2026-11-10",
       "2026-11-11",
       "2026-11-12",
       "2026-11-13",
       "2026-11-14",
       "2026-11-15",
       "2026-11-16"
      ],
      "total": 4530,
      "delivered": 4442,
      "failed": 88,
      "failure_rate_pct": 1.9,
      "requests_per_day": {
       "2026-11-10": 773,
       "2026-11-11": 740,
       "2026-11-12": 703,
       "2026-11-13": 776,
       "2026-11-14": 632,
       "2026-11-15": 531,
       "2026-11-16": 375
      },
      "failure_rate_pct_per_day": {
       "2026-11-10": 1.6,
       "2026-11-11": 2.4,
       "2026-11-12": 1.3,
       "2026-11-13": 2.2,
       "2026-11-14": 1.7,
       "2026-11-15": 2.3,
       "2026-11-16": 2.4
      },
      "days_without_data": [],
      "failure_reasons": [
       {
        "reason": "Recipient unreachable",
        "meaning": "The provider could not reach the recipient's phone (switched off, no coverage or full inbox).",
        "category": "Recipient device",
        "who_fixes": "Usually nothing to fix on the sending side; the phone is off, full or out of coverage.",
        "count": 51
       },
       {
        "reason": "Recipient opted out",
        "meaning": "The recipient has chosen not to receive messages of this kind.",
        "category": "Opt-out preference",
        "who_fixes": "The recipient's own preference; if it hits verification codes, check the message category registered with the provider.",
        "count": 25
       },
       {
        "reason": "Message expired",
        "meaning": "The message waited too long for delivery and the provider dropped it.",
        "category": "Network",
        "who_fixes": "Usually nothing to fix on the sending side; a temporary operator or network problem. Persistent cases go to the provider.",
        "count": 12
       }
      ],
      "failures_by_category": {
       "Recipient device": 51,
       "Opt-out preference": 25,
       "Network": 12
      },
      "templates": [
       [
        "tpl-0001",
        2742
       ],
       [
        "tpl-0002",
        1126
       ],
       [
        "tpl-0003",
        662
       ]
      ],
      "distinct_recipients": 501,
      "recipient_digit_lengths": {
       "12": 4530
      },
      "notes": [],
      "failures_by_group": {
       "route": {
        "whole_window": [
         {
          "value": "5",
          "requests": 1143,
          "failed": 24,
          "failure_rate_pct": 2.1
         },
         {
          "value": "4",
          "requests": 3387,
          "failed": 64,
          "failure_rate_pct": 1.9
         }
        ],
        "latest_day": [
         {
          "value": "4",
          "requests": 288,
          "failed": 9,
          "failure_rate_pct": 3.1
         },
         {
          "value": "5",
          "requests": 87,
          "failed": 0,
          "failure_rate_pct": 0.0
         }
        ]
       },
       "sender": {
        "whole_window": [
         {
          "value": "MOCKA",
          "requests": 3130,
          "failed": 65,
          "failure_rate_pct": 2.1
         },
         {
          "value": "MOCKB",
          "requests": 1400,
          "failed": 23,
          "failure_rate_pct": 1.6
         }
        ],
        "latest_day": [
         {
          "value": "MOCKA",
          "requests": 264,
          "failed": 7,
          "failure_rate_pct": 2.7
         },
         {
          "value": "MOCKB",
          "requests": 111,
          "failed": 2,
          "failure_rate_pct": 1.8
         }
        ]
       },
       "template": {
        "whole_window": [
         {
          "value": "tpl-0003",
          "requests": 662,
          "failed": 16,
          "failure_rate_pct": 2.4
         },
         {
          "value": "tpl-0001",
          "requests": 2742,
          "failed": 51,
          "failure_rate_pct": 1.9
         },
         {
          "value": "tpl-0002",
          "requests": 1126,
          "failed": 21,
          "failure_rate_pct": 1.9
         }
        ],
        "latest_day": [
         {
          "value": "tpl-0001",
          "requests": 237,
          "failed": 7,
          "failure_rate_pct": 3.0
         },
         {
          "value": "tpl-0003",
          "requests": 53,
          "failed": 1,
          "failure_rate_pct": 1.9
         },
         {
          "value": "tpl-0002",
          "requests": 85,
          "failed": 1,
          "failure_rate_pct": 1.2
         }
        ]
       }
      },
      "latest_day_utc": "2026-11-16",
      "failures_by_hour_latest_day": [
       {
        "hour": 0,
        "requests": 8,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 1,
        "requests": 7,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 2,
        "requests": 5,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 3,
        "requests": 6,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 4,
        "requests": 8,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 5,
        "requests": 10,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 6,
        "requests": 24,
        "failed": 1,
        "failure_rate_pct": 4.2
       },
       {
        "hour": 7,
        "requests": 42,
        "failed": 1,
        "failure_rate_pct": 2.4
       },
       {
        "hour": 8,
        "requests": 61,
        "failed": 4,
        "failure_rate_pct": 6.6
       },
       {
        "hour": 9,
        "requests": 61,
        "failed": 1,
        "failure_rate_pct": 1.6
       },
       {
        "hour": 10,
        "requests": 85,
        "failed": 1,
        "failure_rate_pct": 1.2
       },
       {
        "hour": 11,
        "requests": 58,
        "failed": 1,
        "failure_rate_pct": 1.7
       }
      ],
      "concentration": null,
      "repeat_requests": {
       "window_minutes": 10,
       "recipients_with_a_repeat": 127,
       "repeat_requests": 153,
       "recipients_with_two_or_more_repeats": 21,
       "share_of_requests_pct": 3.4,
       "share_of_requests_pct_per_day": {
        "2026-11-10": 1.4,
        "2026-11-11": 1.5,
        "2026-11-12": 0.7,
        "2026-11-13": 2.1,
        "2026-11-14": 2.4,
        "2026-11-15": 0.8,
        "2026-11-16": 24.3
       },
       "note": "A repeat is a request for the same number within the code validity window of the one before. A newer code replaces the older one, so repeats are one reason a code typed by the user can be 'invalid'. The logs cannot show which code the user typed."
      },
      "delivery_delay_s": {
       "median": 6.0,
       "p90": 9.0,
       "max": 9.0
      }
     },
     "shortened_for_display": false
    }
   ],
   "report": "[SCRIPTED STAND-IN, NOT AI] The text below comes from fixed keyword rules and a template, not from a language model. It only repeats numbers from the tool results and can miss or misread anything.\n\n1) Verdict\nRule-based reading: 24.3 percent of requests on the latest day are repeats within the validity window, and a newer code replaces an older one. Confidence: low to medium; check the evidence yourself. [E1]\n\n2) Evidence\n- Volume: 4530 requests over 7 days, 88 failed (1.9 percent) [E1]\n- Requests per day [E1]\n  - 10 Nov: 773 requests, 1.6 percent failed\n  - 11 Nov: 740 requests, 2.4 percent failed\n  - 12 Nov: 703 requests, 1.3 percent failed\n  - 13 Nov: 776 requests, 2.2 percent failed\n  - 14 Nov: 632 requests, 1.7 percent failed\n  - 15 Nov: 531 requests, 2.3 percent failed\n  - 16 Nov: 375 requests, 2.4 percent failed\n- Most common failure reason: Recipient unreachable (51 rows). Category: Recipient device. Who fixes it: Usually nothing to fix on the sending side; the phone is off, full or out of coverage. [E1]\n- Repeat requests: 127 recipients, 3.4 percent of requests [E1]\n- Delivery delay at the provider: median 6.0 s, p90 9.0 s, max 9.0 s [E1]\n\n3) Not checked / limits\n- Checks that ran: fetch_delivery_logs. This scripted stand-in does not decide which causes are ruled out, so treat every other cause as not yet checked [E1].\n- Not visible to any tool here: the API server's own log, the database scheduler, the code that validates a code, and anything outside the configured sources.\n- check_numbers was not run: the PM gave no phone numbers.\n- check_code_api was not run: the API check is switched off.\n\n4) Suggested next steps\n- Ask engineering how the server decides which code to accept when more than one is active. To test: request two codes in a row and enter the first one.\n\n5) Information needed from you: None.\nOptional checks that are switched off in this run: phone-number lookup (use --number or --prompt-numbers) and the test-message check of the verification API (set PROBE_ENABLED and use --approve-probe; it sends one real message to your own test number).",
   "eval": {
    "expected_outcome": "cause_found",
    "outcome_from_report": "cause_found",
    "checks_passed": 7,
    "checks_total": 7,
    "failed_checks": [],
    "scored_by": "evals/run_evals.py score() applied to this recorded report"
   },
   "cost_line": "This round: no language model was used (scripted stand-in), cost 0.",
   "source": "python3 investigate.py --demo --mock-scenario S21 \"<question>\"",
   "source_kind": "scripted_stand_in"
  },
  {
   "id": "S2",
   "title": "Provider outage on one route",
   "question": "Verification codes are not arriving for many users since the early morning. What is wrong?",
   "expected_outcome": "cause_found",
   "banner": "[SCRIPTED STAND-IN, NOT AI] The text below comes from fixed keyword rules and a template, not from a language model. It only repeats numbers from the tool results and can miss or misread anything.",
   "tools_unavailable": "not available this run: check_numbers (the PM gave no phone numbers (use --number, --numbers-file or --prompt-numbers)), check_code_api (the API check is switched off (PROBE_ENABLED is not true; the PM can turn it on and approve each run))",
   "calls": [
    {
     "id": "E1",
     "tool": "fetch_delivery_logs",
     "args": {
      "start_date": "2026-11-10",
      "end_date": "2026-11-16"
     },
     "result": {
      "source": "provider_live_api",
      "days": [
       "2026-11-10",
       "2026-11-11",
       "2026-11-12",
       "2026-11-13",
       "2026-11-14",
       "2026-11-15",
       "2026-11-16"
      ],
      "total": 4610,
      "delivered": 4448,
      "failed": 162,
      "failure_rate_pct": 3.5,
      "requests_per_day": {
       "2026-11-10": 832,
       "2026-11-11": 791,
       "2026-11-12": 775,
       "2026-11-13": 765,
       "2026-11-14": 617,
       "2026-11-15": 559,
       "2026-11-16": 271
      },
      "failure_rate_pct_per_day": {
       "2026-11-10": 3.0,
       "2026-11-11": 1.8,
       "2026-11-12": 3.0,
       "2026-11-13": 2.2,
       "2026-11-14": 1.9,
       "2026-11-15": 1.8,
       "2026-11-16": 22.5
      },
      "days_without_data": [],
      "failure_reasons": [
       {
        "reason": "Recipient unreachable",
        "meaning": "The provider could not reach the recipient's phone (switched off, no coverage or full inbox).",
        "category": "Recipient device",
        "who_fixes": "Usually nothing to fix on the sending side; the phone is off, full or out of coverage.",
        "count": 59
       },
       {
        "reason": "Network failure",
        "meaning": "The operator network did not accept or confirm the message in time.",
        "category": "Network",
        "who_fixes": "Usually nothing to fix on the sending side; a temporary operator or network problem. Persistent cases go to the provider.",
        "count": 58
       },
       {
        "reason": "Recipient opted out",
        "meaning": "The recipient has chosen not to receive messages of this kind.",
        "category": "Opt-out preference",
        "who_fixes": "The recipient's own preference; if it hits verification codes, check the message category registered with the provider.",
        "count": 27
       },
       {
        "reason": "Message expired",
        "meaning": "The message waited too long for delivery and the provider dropped it.",
        "category": "Network",
        "who_fixes": "Usually nothing to fix on the sending side; a temporary operator or network problem. Persistent cases go to the provider.",
        "count": 18
       }
      ],
      "failures_by_category": {
       "Network": 76,
       "Recipient device": 59,
       "Opt-out preference": 27
      },
      "templates": [
       [
        "tpl-0001",
        2671
       ],
       [
        "tpl-0002",
        1222
       ],
       [
        "tpl-0003",
        717
       ]
      ],
      "distinct_recipients": 501,
      "recipient_digit_lengths": {
       "12": 4610
      },
      "notes": [],
      "failures_by_group": {
       "route": {
        "whole_window": [
         {
          "value": "5",
          "requests": 1163,
          "failed": 81,
          "failure_rate_pct": 7.0
         },
         {
          "value": "4",
          "requests": 3447,
          "failed": 81,
          "failure_rate_pct": 2.3
         }
        ],
        "latest_day": [
         {
          "value": "5",
          "requests": 73,
          "failed": 58,
          "failure_rate_pct": 79.5
         },
         {
          "value": "4",
          "requests": 198,
          "failed": 3,
          "failure_rate_pct": 1.5
         }
        ]
       },
       "sender": {
        "whole_window": [
         {
          "value": "MOCKA",
          "requests": 3200,
          "failed": 112,
          "failure_rate_pct": 3.5
         },
         {
          "value": "MOCKB",
          "requests": 1410,
          "failed": 50,
          "failure_rate_pct": 3.5
         }
        ],
        "latest_day": [
         {
          "value": "MOCKB",
          "requests": 90,
          "failed": 21,
          "failure_rate_pct": 23.3
         },
         {
          "value": "MOCKA",
          "requests": 181,
          "failed": 40,
          "failure_rate_pct": 22.1
         }
        ]
       },
       "template": {
        "whole_window": [
         {
          "value": "tpl-0003",
          "requests": 717,
          "failed": 28,
          "failure_rate_pct": 3.9
         },
         {
          "value": "tpl-0002",
          "requests": 1222,
          "failed": 45,
          "failure_rate_pct": 3.7
         },
         {
          "value": "tpl-0001",
          "requests": 2671,
          "failed": 89,
          "failure_rate_pct": 3.3
         }
        ],
        "latest_day": [
         {
          "value": "tpl-0003",
          "requests": 45,
          "failed": 14,
          "failure_rate_pct": 31.1
         },
         {
          "value": "tpl-0002",
          "requests": 61,
          "failed": 17,
          "failure_rate_pct": 27.9
         },
         {
          "value": "tpl-0001",
          "requests": 165,
          "failed": 30,
          "failure_rate_pct": 18.2
         }
        ]
       }
      },
      "latest_day_utc": "2026-11-16",
      "failures_by_hour_latest_day": [
       {
        "hour": 0,
        "requests": 3,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 1,
        "requests": 9,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 3,
        "requests": 2,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 4,
        "requests": 7,
        "failed": 1,
        "failure_rate_pct": 14.3
       },
       {
        "hour": 5,
        "requests": 8,
        "failed": 3,
        "failure_rate_pct": 37.5
       },
       {
        "hour": 6,
        "requests": 18,
        "failed": 3,
        "failure_rate_pct": 16.7
       },
       {
        "hour": 7,
        "requests": 33,
        "failed": 3,
        "failure_rate_pct": 9.1
       },
       {
        "hour": 8,
        "requests": 45,
        "failed": 12,
        "failure_rate_pct": 26.7
       },
       {
        "hour": 9,
        "requests": 48,
        "failed": 14,
        "failure_rate_pct": 29.2
       },
       {
        "hour": 10,
        "requests": 48,
        "failed": 15,
        "failure_rate_pct": 31.2
       },
       {
        "hour": 11,
        "requests": 50,
        "failed": 10,
        "failure_rate_pct": 20.0
       }
      ],
      "concentration": {
       "dimension": "route",
       "value": "5",
       "failure_rate_pct": 79.5,
       "other_rate_pct": 1.5,
       "share_of_failures_pct": 95.1,
       "first_bad_hour_utc": 4
      },
      "repeat_requests": {
       "window_minutes": 10,
       "recipients_with_a_repeat": 55,
       "repeat_requests": 59,
       "recipients_with_two_or_more_repeats": 4,
       "share_of_requests_pct": 1.3,
       "share_of_requests_pct_per_day": {
        "2026-11-10": 1.1,
        "2026-11-11": 1.3,
        "2026-11-12": 1.2,
        "2026-11-13": 2.2,
        "2026-11-14": 1.0,
        "2026-11-15": 1.3,
        "2026-11-16": 0.4
       },
       "note": "A repeat is a request for the same number within the code validity window of the one before. A newer code replaces the older one, so repeats are one reason a code typed by the user can be 'invalid'. The logs cannot show which code the user typed."
      },
      "delivery_delay_s": {
       "median": 6.0,
       "p90": 9.0,
       "max": 9.0
      }
     },
     "shortened_for_display": false
    },
    {
     "id": "E2",
     "tool": "get_credit_balance",
     "args": {},
     "result": {
      "balance": 4200.0,
      "requests_remaining_at_current_rate": 84000,
      "note": "Credit is shared by every message type on the account. This is the balance now; it does not show the balance at an earlier time."
     },
     "shortened_for_display": false
    }
   ],
   "report": "[SCRIPTED STAND-IN, NOT AI] The text below comes from fixed keyword rules and a template, not from a language model. It only repeats numbers from the tool results and can miss or misread anything.\n\n1) Verdict\nRule-based reading: on the latest day 79.5% of requests on route 5 failed, against 1.5% on other routes, starting around 04:00 UTC. The failures are concentrated on route 5, not spread evenly. Confidence: low to medium; check the evidence yourself. [E1]\n\n2) Evidence\n- Volume: 4610 requests over 7 days, 162 failed (3.5 percent) [E1]\n- Requests per day [E1]\n  - 10 Nov: 832 requests, 3 percent failed\n  - 11 Nov: 791 requests, 1.8 percent failed\n  - 12 Nov: 775 requests, 3 percent failed\n  - 13 Nov: 765 requests, 2.2 percent failed\n  - 14 Nov: 617 requests, 1.9 percent failed\n  - 15 Nov: 559 requests, 1.8 percent failed\n  - 16 Nov: 271 requests, 22.5 percent failed\n- Failures by route on the latest day [E1]\n  - route 5: 79.5 percent of 73 requests failed\n  - route 4: 1.5 percent of 198 requests failed\n- Most common failure reason: Recipient unreachable (59 rows). Category: Recipient device. Who fixes it: Usually nothing to fix on the sending side; the phone is off, full or out of coverage. [E1]\n- Delivery delay at the provider: median 6.0 s, p90 9.0 s, max 9.0 s [E1]\n- Credit balance now: 4200.0 [E2]\n\n3) Not checked / limits\n- Checks that ran: fetch_delivery_logs, get_credit_balance. This scripted stand-in does not decide which causes are ruled out, so treat every other cause as not yet checked [E1].\n- Not visible to any tool here: the API server's own log, the database scheduler, the code that validates a code, and anything outside the configured sources.\n- check_numbers was not run: the PM gave no phone numbers.\n- check_code_api was not run: the API check is switched off.\n\n4) Suggested next steps\n- Ask your provider whether route 5 had an incident from about 04:00 UTC on 16 Nov; compare against that route's rate in earlier days; if you can, send through another route meanwhile.\n\n5) Information needed from you: None.\nOptional checks that are switched off in this run: phone-number lookup (use --number or --prompt-numbers) and the test-message check of the verification API (set PROBE_ENABLED and use --approve-probe; it sends one real message to your own test number).",
   "eval": {
    "expected_outcome": "cause_found",
    "outcome_from_report": "cause_found",
    "checks_passed": 7,
    "checks_total": 7,
    "failed_checks": [],
    "scored_by": "evals/run_evals.py score() applied to this recorded report"
   },
   "cost_line": "This round: no language model was used (scripted stand-in), cost 0.",
   "source": "python3 investigate.py --demo --mock-scenario S2 \"<question>\"",
   "source_kind": "scripted_stand_in"
  },
  {
   "id": "S8",
   "title": "Unanswerable: the cause is outside the configured sources",
   "question": "Verification code requests seem to have dropped since the early morning. Why?",
   "expected_outcome": "inconclusive",
   "banner": "[SCRIPTED STAND-IN, NOT AI] The text below comes from fixed keyword rules and a template, not from a language model. It only repeats numbers from the tool results and can miss or misread anything.",
   "tools_unavailable": "not available this run: check_numbers (the PM gave no phone numbers (use --number, --numbers-file or --prompt-numbers)), check_code_api (the API check is switched off (PROBE_ENABLED is not true; the PM can turn it on and approve each run))",
   "calls": [
    {
     "id": "E1",
     "tool": "fetch_delivery_logs",
     "args": {
      "start_date": "2026-11-10",
      "end_date": "2026-11-16"
     },
     "result": {
      "source": "provider_live_api",
      "days": [
       "2026-11-10",
       "2026-11-11",
       "2026-11-12",
       "2026-11-13",
       "2026-11-14",
       "2026-11-15",
       "2026-11-16"
      ],
      "total": 4319,
      "delivered": 4229,
      "failed": 90,
      "failure_rate_pct": 2.1,
      "requests_per_day": {
       "2026-11-10": 786,
       "2026-11-11": 755,
       "2026-11-12": 746,
       "2026-11-13": 796,
       "2026-11-14": 590,
       "2026-11-15": 518,
       "2026-11-16": 128
      },
      "failure_rate_pct_per_day": {
       "2026-11-10": 2.4,
       "2026-11-11": 1.6,
       "2026-11-12": 2.4,
       "2026-11-13": 2.1,
       "2026-11-14": 1.7,
       "2026-11-15": 2.1,
       "2026-11-16": 2.3
      },
      "days_without_data": [],
      "failure_reasons": [
       {
        "reason": "Recipient unreachable",
        "meaning": "The provider could not reach the recipient's phone (switched off, no coverage or full inbox).",
        "category": "Recipient device",
        "who_fixes": "Usually nothing to fix on the sending side; the phone is off, full or out of coverage.",
        "count": 52
       },
       {
        "reason": "Recipient opted out",
        "meaning": "The recipient has chosen not to receive messages of this kind.",
        "category": "Opt-out preference",
        "who_fixes": "The recipient's own preference; if it hits verification codes, check the message category registered with the provider.",
        "count": 27
       },
       {
        "reason": "Message expired",
        "meaning": "The message waited too long for delivery and the provider dropped it.",
        "category": "Network",
        "who_fixes": "Usually nothing to fix on the sending side; a temporary operator or network problem. Persistent cases go to the provider.",
        "count": 11
       }
      ],
      "failures_by_category": {
       "Recipient device": 52,
       "Opt-out preference": 27,
       "Network": 11
      },
      "templates": [
       [
        "tpl-0001",
        2618
       ],
       [
        "tpl-0002",
        1092
       ],
       [
        "tpl-0003",
        609
       ]
      ],
      "distinct_recipients": 501,
      "recipient_digit_lengths": {
       "12": 4319
      },
      "notes": [],
      "failures_by_group": {
       "route": {
        "whole_window": [
         {
          "value": "5",
          "requests": 1075,
          "failed": 31,
          "failure_rate_pct": 2.9
         },
         {
          "value": "4",
          "requests": 3244,
          "failed": 59,
          "failure_rate_pct": 1.8
         }
        ],
        "latest_day": [
         {
          "value": "5",
          "requests": 25,
          "failed": 1,
          "failure_rate_pct": 4.0
         },
         {
          "value": "4",
          "requests": 103,
          "failed": 2,
          "failure_rate_pct": 1.9
         }
        ]
       },
       "sender": {
        "whole_window": [
         {
          "value": "MOCKA",
          "requests": 3047,
          "failed": 64,
          "failure_rate_pct": 2.1
         },
         {
          "value": "MOCKB",
          "requests": 1272,
          "failed": 26,
          "failure_rate_pct": 2.0
         }
        ],
        "latest_day": [
         {
          "value": "MOCKB",
          "requests": 30,
          "failed": 1,
          "failure_rate_pct": 3.3
         },
         {
          "value": "MOCKA",
          "requests": 98,
          "failed": 2,
          "failure_rate_pct": 2.0
         }
        ]
       },
       "template": {
        "whole_window": [
         {
          "value": "tpl-0001",
          "requests": 2618,
          "failed": 59,
          "failure_rate_pct": 2.3
         },
         {
          "value": "tpl-0002",
          "requests": 1092,
          "failed": 22,
          "failure_rate_pct": 2.0
         },
         {
          "value": "tpl-0003",
          "requests": 609,
          "failed": 9,
          "failure_rate_pct": 1.5
         }
        ],
        "latest_day": [
         {
          "value": "tpl-0002",
          "requests": 25,
          "failed": 1,
          "failure_rate_pct": 4.0
         },
         {
          "value": "tpl-0001",
          "requests": 84,
          "failed": 2,
          "failure_rate_pct": 2.4
         }
        ]
       }
      },
      "latest_day_utc": "2026-11-16",
      "failures_by_hour_latest_day": [
       {
        "hour": 0,
        "requests": 2,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 1,
        "requests": 3,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 2,
        "requests": 2,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 3,
        "requests": 2,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 4,
        "requests": 3,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 5,
        "requests": 1,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 6,
        "requests": 4,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 7,
        "requests": 16,
        "failed": 1,
        "failure_rate_pct": 6.2
       },
       {
        "hour": 8,
        "requests": 24,
        "failed": 1,
        "failure_rate_pct": 4.2
       },
       {
        "hour": 9,
        "requests": 24,
        "failed": 0,
        "failure_rate_pct": 0.0
       },
       {
        "hour": 10,
        "requests": 29,
        "failed": 1,
        "failure_rate_pct": 3.4
       },
       {
        "hour": 11,
        "requests": 18,
        "failed": 0,
        "failure_rate_pct": 0.0
       }
      ],
      "concentration": null,
      "repeat_requests": {
       "window_minutes": 10,
       "recipients_with_a_repeat": 58,
       "repeat_requests": 61,
       "recipients_with_two_or_more_repeats": 3,
       "share_of_requests_pct": 1.4,
       "share_of_requests_pct_per_day": {
        "2026-11-10": 1.5,
        "2026-11-11": 1.5,
        "2026-11-12": 1.6,
        "2026-11-13": 1.9,
        "2026-11-14": 0.8,
        "2026-11-15": 0.8,
        "2026-11-16": 1.6
       },
       "note": "A repeat is a request for the same number within the code validity window of the one before. A newer code replaces the older one, so repeats are one reason a code typed by the user can be 'invalid'. The logs cannot show which code the user typed."
      },
      "delivery_delay_s": {
       "median": 5.0,
       "p90": 9.0,
       "max": 9.0
      },
      "api_failed_calls": {
       "total": 2,
       "by_error_code": [
        {
         "error_code": "E110",
         "count": 2,
         "label": "Duplicate within 20 seconds",
         "meaning": "The same request was received twice within 20 seconds and the second was dropped. Normal on its own."
        }
       ],
       "per_day": {
        "2026-11-15": {
         "E110": 2
        }
       },
       "note": "These calls were refused before submission, so they have no row in the delivery logs. E110 (duplicate within 20 seconds) is normal at a low level."
      }
     },
     "shortened_for_display": false
    },
    {
     "id": "E2",
     "tool": "get_credit_balance",
     "args": {},
     "result": {
      "balance": 4200.0,
      "requests_remaining_at_current_rate": 84000,
      "note": "Credit is shared by every message type on the account. This is the balance now; it does not show the balance at an earlier time."
     },
     "shortened_for_display": false
    }
   ],
   "report": "[SCRIPTED STAND-IN, NOT AI] The text below comes from fixed keyword rules and a template, not from a language model. It only repeats numbers from the tool results and can miss or misread anything.\n\n1) Verdict\nNo clear fault found by the fixed rules. Confidence: low. This is not proof that nothing is wrong. [E1]\n\n2) Evidence\n- Volume: 4319 requests over 7 days, 90 failed (2.1 percent) [E1]\n- Requests per day [E1]\n  - 10 Nov: 786 requests, 2.4 percent failed\n  - 11 Nov: 755 requests, 1.6 percent failed\n  - 12 Nov: 746 requests, 2.4 percent failed\n  - 13 Nov: 796 requests, 2.1 percent failed\n  - 14 Nov: 590 requests, 1.7 percent failed\n  - 15 Nov: 518 requests, 2.1 percent failed\n  - 16 Nov: 128 requests, 2.3 percent failed\n- Most common failure reason: Recipient unreachable (52 rows). Category: Recipient device. Who fixes it: Usually nothing to fix on the sending side; the phone is off, full or out of coverage. [E1]\n- Delivery delay at the provider: median 5.0 s, p90 9.0 s, max 9.0 s [E1]\n- Credit balance now: 4200.0 [E2]\n\n3) Not checked / limits\n- Checks that ran: fetch_delivery_logs, get_credit_balance. This scripted stand-in does not decide which causes are ruled out, so treat every other cause as not yet checked [E1].\n- Not visible to any tool here: the API server's own log, the database scheduler, the code that validates a code, and anything outside the configured sources.\n- check_numbers was not run: the PM gave no phone numbers.\n- check_code_api was not run: the API check is switched off.\n\n4) Suggested next steps\n- Add a more specific symptom or the affected dates and run again.\n\n5) Information needed from you\n1. The dates and times when people saw the problem, and which app or screen they used\n   - Why: the rules read a whole window and can miss a short or narrow fault\n   - How or who to ask: ask the people who reported it, then run again with those dates in the question\n2. One or two phone numbers of affected users\n   - Why: the tool can then look at those users' requests and repeats (it sees aliases such as N1, never the numbers)\n   - How or who to ask: use --number or --prompt-numbers\n3. The verification API server's own log for a time when it failed\n   - Why: some faults leave nothing in the delivery log and no tool here can read that log\n   - How or who to ask: ask engineering\n\nOptional checks that are switched off in this run: the test-message check of the verification API (set PROBE_ENABLED and use --approve-probe; it sends one real message to your own test number).",
   "eval": {
    "expected_outcome": "inconclusive",
    "outcome_from_report": "no_issue",
    "checks_passed": 4,
    "checks_total": 7,
    "failed_checks": [
     "outcome",
     "must_mention",
     "shortest_path"
    ],
    "scored_by": "evals/run_evals.py score() applied to this recorded report"
   },
   "cost_line": "This round: no language model was used (scripted stand-in), cost 0.",
   "source": "python3 investigate.py --demo --mock-scenario S8 \"<question>\"",
   "source_kind": "scripted_stand_in"
  },
  {
   "id": "S2-real",
   "title": "Provider outage on one route, answered by a real model",
   "question": "Verification codes are not arriving for many users since the early morning. What is wrong?",
   "expected_outcome": "cause_found",
   "source_kind": "real_model",
   "model": "claude-sonnet-5-5",
   "provider": "anthropic",
   "run_date": "2026-11-18",
   "scenario": "S2",
   "calls": [
    {
     "id": "E1",
     "tool": "fetch_delivery_logs",
     "result_saved": false
    },
    {
     "id": "E2",
     "tool": "get_credit_balance",
     "result_saved": false
    },
    {
     "id": "E3",
     "tool": "check_message_queue",
     "result_saved": false
    },
    {
     "id": "E4",
     "tool": "recent_code_changes",
     "result_saved": false
    }
   ],
   "report": "1) **Verdict:** Most likely a problem on provider route 5, which began around 04:00 UTC today. Confidence is medium. The route is clearly the pattern, but I can't see the reason behind it. [E1]\n\n2) **Evidence**\n- Today's failure rate is 22.5% (61 of 271 requests so far). On the seven earlier days it was 1.8–3.0%. [E1]\n- Route 5 failed on 58 of 73 requests today (79.5%). Route 4 failed on 3 of 198 (1.5%). Route 5 accounts for 95% of today's failures, and the first bad hour was 04:00 UTC. [E1]\n- Today's failures are not tied to one sender (MOCKB 23%, MOCKA 22%) or one template (18–31%). That fits a route-level fault better than a sender or template fault. [E1]\n- The failure reasons are all recipient-side or network: Recipient unreachable (65), Network failure (58), Recipient opted out (30) and Message expired (20). The glossary says Network failure and Message expired are usually temporary operator or network problems, and persistent cases go to the provider. [E1]\n- These reason counts cover the whole 9–16 Nov window, not just today. I can't tell which reasons make up today's spike. [E1]\n- Messages that did get through were fast: median delay 6 seconds and maximum 9 seconds. [E1]\n- Every SMS row since 9 Nov was handed to the provider within 30 seconds, and nothing is waiting in the queue. The newest row is from 11:58 UTC. So messages are being sent, not held back. [E3]\n- Today's request volume looks normal so far: 271 by 12:00 UTC, against 510–832 for full earlier days. This is a partial day, so I can't call it a drop. [E1]\n\n3) **Not checked / limits**\n- **Ruled out:**\n  - Credit exhaustion: the balance is 4,200 now and there is no volume drop. This is the balance now, not at 04:00. [E2][E1]\n  - Template or registration failure: no Registration category and no single template carrying the failures. [E1]\n  - Late delivery from queue delay: all rows were sent in under 30 seconds. [E3]\n  - Missing log files: none. [E1]\n  - Repeated requests replacing codes: only 0.4% of requests today, so not a driver. [E1]\n  - Code changes: recent commits touch only logging, wording and retry, and I read subjects and file names, not the code. [E4]\n  - Short numbers from an empty dial code: all recipients have 12 digits. [E1]\n- **Still open or not checkable:**\n  - Why route 5 is failing. This is a provider or operator question that no tool here can answer.\n  - Stale or rejected API credential: not tested. The API check was not run, and the request volume suggests requests reach the provider.\n  - Empty dial codes in user records: I didn't run the user-data check, and counts there are current, not historical.\n  - Stopped scheduled database jobs: no tool can see them. The queue looks current, so there is no sign of a problem.\n  - Per-number checks: unavailable because you gave no phone numbers.\n  - An older code still working after a newer one was issued: this is a code-level fault that no tool here can test.\n  - SENT only means handed to the provider, not received. The queue check also can't tell code messages from other texts. [E3]\n\n4) **Suggested next steps**\n- Ask the provider whether route 5 has an incident or operator problem since about 04:00 UTC today. Quote the failure rate of about 80%.\n- If route 5 is the problem, ask engineering whether traffic can be moved to route 4. Route 4 is healthy, with a 1.5% failure rate today. [E1]\n- Re-run the delivery-log check in an hour to see whether the failure rate is falling.\n- Tell affected users to request a new code, but only once. A new request replaces the earlier code.\n\n5) **Information needed from you**\n1. Provider status or incident notice for route 5, 16 Nov from 04:00 UTC. It would confirm or rule out a provider-side fault. Ask your messaging provider's support, or check their status page, and send a typed note.\n2. Which route engineering configured as route 5, and whether it was changed recently. It would show whether this is a configuration problem on our side. Ask engineering or DevOps for a typed note.\n3. A delivery-log export (CSV, UTC, failed rows included) for 16 Nov only. It would show the failure reasons for today alone. The current reason counts mix all eight days. Export it from the provider.",
   "eval": {
    "expected_outcome": "cause_found",
    "outcome_from_report": "cause_found",
    "checks_passed": 7,
    "checks_total": 7,
    "failed_checks": [],
    "scored_by": "evals/run_evals.py score(), saved in evals/published/real_model_v1.0.0.json"
   },
   "usage": {
    "input_tokens": 14299,
    "output_tokens": 2390,
    "model_calls": 2,
    "seconds": 22.5
   },
   "source": "evals/published/real_model_v1.0.0.json (scenario S2)"
  }
 ],
 "facts": {
  "scenarios": 22,
  "tests": 211,
  "stand_in_checks_passed": 115,
  "stand_in_checks_total": 154,
  "stand_in_scenarios_all_passed": 4,
  "model_results": "Real-model results from one run are in evals/published/ (see docs/EVALUATION_RESULTS.md)",
  "real_model": {
   "model": "claude-sonnet-5-5",
   "date": "2026-11-18",
   "scenarios": 22,
   "checks_passed": 129,
   "checks_total": 154,
   "scenarios_all_passed": 8,
   "spend_usd": 1.78,
   "per_check": {
    "outcome": "14/22",
    "cause_category": "21/22",
    "must_mention": "13/22",
    "must_not_claim": "21/22",
    "shortest_path": "16/22",
    "citations": "22/22",
    "section5": "22/22"
   }
  }
 }
};
