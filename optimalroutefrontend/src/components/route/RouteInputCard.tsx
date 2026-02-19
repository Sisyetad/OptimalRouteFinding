"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Form } from "@/components/ui/form";
import { useState } from "react";

const schema = z.object({
  start: z.string().min(2, "Enter a valid start location"),
  end: z.string().min(2, "Enter a valid destination"),
});

type FormValues = z.infer<typeof schema>;

export function RouteInputCard({ onSubmit, loading }: { onSubmit: (data: FormValues) => void; loading?: boolean }) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    mode: "onTouched",
  });
  const [touched, setTouched] = useState(false);

  return (
    <Card className="w-full max-w-md mx-auto p-6 rounded-2xl shadow-lg bg-white dark:bg-zinc-900" id="plan-route">
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit((data) => {
            setTouched(true);
            onSubmit(data);
          })}
          className="flex flex-col gap-6"
        >
          <div>
            <Label htmlFor="start">Start Location</Label>
            <Input
              id="start"
              placeholder="e.g. San Francisco, CA"
              {...form.register("start")}
              autoComplete="off"
              className={form.formState.errors.start ? "border-red-500" : ""}
              onBlur={() => setTouched(true)}
            />
            {form.formState.errors.start && (
              <span className="text-xs text-red-500 mt-1 block animate-fade-in">
                {form.formState.errors.start.message}
              </span>
            )}
          </div>
          <div>
            <Label htmlFor="end">Destination</Label>
            <Input
              id="end"
              placeholder="e.g. New York, NY"
              {...form.register("end")}
              autoComplete="off"
              className={form.formState.errors.end ? "border-red-500" : ""}
              onBlur={() => setTouched(true)}
            />
            {form.formState.errors.end && (
              <span className="text-xs text-red-500 mt-1 block animate-fade-in">
                {form.formState.errors.end.message}
              </span>
            )}
          </div>
          <Button type="submit" size="lg" className="mt-2" disabled={loading}>
            {loading ? (
              <span className="animate-pulse">Planning…</span>
            ) : (
              "Plan Route"
            )}
          </Button>
        </form>
      </Form>
    </Card>
  );
}
