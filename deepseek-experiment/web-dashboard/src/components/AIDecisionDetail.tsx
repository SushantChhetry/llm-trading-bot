import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { ChevronDown, ChevronUp, Brain, FileText, Code, MessageSquare } from 'lucide-react';
import { Trade } from '@/types/trading';

interface AIDecisionDetailProps {
  trade: Trade;
}

export function AIDecisionDetail({ trade }: AIDecisionDetailProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const hasLLMData = !!(trade.llm_prompt || trade.llm_raw_response || trade.llm_parsed_decision || trade.llm_reasoning);

  if (!hasLLMData) {
    return null;
  }

  return (
    <div className="border-t pt-3 mt-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors w-full"
      >
        {isExpanded ? (
          <ChevronUp className="h-4 w-4" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )}
        <Brain className="h-4 w-4" />
        <span>AI Decision Details</span>
      </button>

      {isExpanded && (
        <div className="mt-3 space-y-3">
          {trade.llm_reasoning && (
            <Card className="bg-muted/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  Parsed Reason
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm whitespace-pre-wrap">{trade.llm_reasoning}</p>
              </CardContent>
            </Card>
          )}

          {trade.llm_parsed_decision && (
            <Card className="bg-muted/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  Parsed Decision
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="grid grid-cols-2 gap-2">
                  {trade.llm_parsed_decision.action && (
                    <div>
                      <span className="text-muted-foreground">Action:</span>{' '}
                      <Badge variant="outline">{trade.llm_parsed_decision.action.toUpperCase()}</Badge>
                    </div>
                  )}
                  {trade.llm_parsed_decision.direction && (
                    <div>
                      <span className="text-muted-foreground">Direction:</span>{' '}
                      <Badge variant="outline">{trade.llm_parsed_decision.direction.toUpperCase()}</Badge>
                    </div>
                  )}
                  {trade.llm_parsed_decision.confidence !== undefined && (
                    <div>
                      <span className="text-muted-foreground">Confidence:</span>{' '}
                      {(trade.llm_parsed_decision.confidence * 100).toFixed(0)}%
                    </div>
                  )}
                  {trade.llm_parsed_decision.leverage !== undefined && (
                    <div>
                      <span className="text-muted-foreground">Leverage:</span>{' '}
                      {trade.llm_parsed_decision.leverage}x
                    </div>
                  )}
                </div>
                {trade.llm_parsed_decision.justification && (
                  <div className="pt-2 border-t">
                    <span className="text-muted-foreground block mb-1">Justification:</span>
                    <p className="text-sm">{trade.llm_parsed_decision.justification}</p>
                  </div>
                )}
                {trade.llm_parsed_decision.exit_plan && (
                  <div className="pt-2 border-t">
                    <span className="text-muted-foreground block mb-1">Exit Plan:</span>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      {trade.llm_parsed_decision.exit_plan.profit_target !== undefined && (
                        <div>
                          <span className="text-muted-foreground">Target:</span> ${trade.llm_parsed_decision.exit_plan.profit_target.toFixed(2)}
                        </div>
                      )}
                      {trade.llm_parsed_decision.exit_plan.stop_loss !== undefined && (
                        <div>
                          <span className="text-muted-foreground">Stop:</span> ${trade.llm_parsed_decision.exit_plan.stop_loss.toFixed(2)}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {trade.llm_prompt && (
            <Card className="bg-muted/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Prompt Sent to AI
                </CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-xs bg-background p-3 rounded border overflow-x-auto max-h-64 overflow-y-auto">
                  {trade.llm_prompt}
                </pre>
              </CardContent>
            </Card>
          )}

          {trade.llm_raw_response && (
            <Card className="bg-muted/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Code className="h-4 w-4" />
                  Raw AI Response
                </CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-xs bg-background p-3 rounded border overflow-x-auto max-h-64 overflow-y-auto">
                  {typeof trade.llm_raw_response === 'string'
                    ? trade.llm_raw_response
                    : JSON.stringify(trade.llm_raw_response, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
