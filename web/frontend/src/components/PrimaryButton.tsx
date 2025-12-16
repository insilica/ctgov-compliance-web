import type { ButtonProps } from '@trussworks/react-uswds';
import { Button } from '@trussworks/react-uswds';
import clsx from 'clsx';

type PrimaryButtonProps = Omit<ButtonProps, 'type'> & {
  type?: ButtonProps['type'];
  isLoading?: boolean;
};

export function PrimaryButton({
  className,
  isLoading,
  children,
  disabled,
  type = 'button',
  ...props
}: PrimaryButtonProps) {
  return (
    <Button
      {...props}
      type={type}
      className={clsx('usa-button', 'usa-button--big', className)}
      disabled={isLoading || disabled}
    >
      {isLoading ? 'Loading…' : children}
    </Button>
  );
}
